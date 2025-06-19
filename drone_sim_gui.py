import sys
import traceback
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QLineEdit, QFormLayout, QDialog,
    QMessageBox, QMenuBar, QMenu, QAction, QTabWidget, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QPoint, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from datetime import datetime, time
import numpy as np
from shapely.geometry import Polygon, Point

from astar import astar
from data import drones, deliveries, no_fly_zones
from plot_utils import plot_map, animate_drone_path, plot_statistics
from utils import (
    calculate_distance, calculate_energy, check_time_window,
    is_drone_available, get_available_drones, get_available_deliveries,
    calculate_delivery_score, sort_deliveries_by_priority
)
from dialogs import AddDroneDialog, AddDeliveryDialog, AddNoFlyZoneDialog
from genetic_algorithm import optimize_routes

class DroneSimWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drone Delivery Simulation")
        self.setGeometry(100, 100, 1600, 900)
        
        # Initialize state
        self.drawing_polygon = False
        self.current_polygon_points = []
        self.selected_delivery = None
        self.animations = []
        self.simulation_running = False
        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self.simulation_step)
        
        self.setup_ui()
        self.setup_menu()
        self.reset_simulation()
        
    def setup_menu(self):
        """Set up the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        new_action = QAction('New Simulation', self)
        new_action.triggered.connect(self.reset_simulation)
        file_menu.addAction(new_action)
        
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Add menu
        add_menu = menubar.addMenu('Add')
        
        add_drone_action = QAction('Add Drone', self)
        add_drone_action.triggered.connect(self.add_drone)
        add_menu.addAction(add_drone_action)
        
        add_delivery_action = QAction('Add Delivery', self)
        add_delivery_action.triggered.connect(self.start_add_delivery)
        add_menu.addAction(add_delivery_action)
        
        add_zone_action = QAction('Add No-Fly Zone', self)
        add_zone_action.triggered.connect(self.start_draw_zone)
        add_menu.addAction(add_zone_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        show_stats_action = QAction('Show Statistics', self)
        show_stats_action.triggered.connect(self.show_statistics)
        view_menu.addAction(show_stats_action)
        
    def setup_ui(self):
        """Set up the main UI components"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel (Map)
        map_widget = QWidget()
        map_layout = QVBoxLayout(map_widget)
        
        # Map figure
        self.figure = Figure(figsize=(8, 8))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Add navigation toolbar
        toolbar = NavigationToolbar(self.canvas, map_widget)
        map_layout.addWidget(toolbar)
        map_layout.addWidget(self.canvas)
        
        # Connect mouse events
        self.canvas.mpl_connect('button_press_event', self.on_map_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_map_motion)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Simulation")
        self.reset_btn = QPushButton("Reset")
        self.optimize_btn = QPushButton("Optimize Routes")
        
        self.start_btn.clicked.connect(self.start_simulation)
        self.reset_btn.clicked.connect(self.reset_simulation)
        self.optimize_btn.clicked.connect(self.optimize_routes)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.optimize_btn)
        map_layout.addLayout(button_layout)
        
        # Right panel (Tabs)
        right_panel = QTabWidget()
        
        # Status tab
        status_tab = QWidget()
        status_layout = QVBoxLayout(status_tab)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        
        # Statistics tab
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        self.stats_figure = Figure(figsize=(6, 8))
        self.stats_canvas = FigureCanvas(self.stats_figure)
        self.stats_ax = self.stats_figure.add_subplot(111)
        stats_layout.addWidget(self.stats_canvas)
        
        # Drones tab
        drones_tab = QWidget()
        drones_layout = QVBoxLayout(drones_tab)
        
        self.drones_table = QTableWidget()
        self.drones_table.setColumnCount(5)
        self.drones_table.setHorizontalHeaderLabels([
            'ID', 'Battery Left', 'Max Weight', 'Current Position', 'Status'
        ])
        self.drones_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        drones_layout.addWidget(self.drones_table)
        
        # Add tabs
        right_panel.addTab(status_tab, "Status")
        right_panel.addTab(stats_tab, "Statistics")
        right_panel.addTab(drones_tab, "Drones")
        
        # Add widgets to splitter
        splitter.addWidget(map_widget)
        splitter.addWidget(right_panel)
        splitter.setSizes([1000, 400])
        
    def on_map_click(self, event):
        """Handle map clicks for adding deliveries and drawing zones"""
        if event.inaxes != self.ax:
            return
            
        x, y = event.xdata, event.ydata
        
        if self.drawing_polygon:
            self.current_polygon_points.append((x, y))
            self.update_polygon_preview()
        elif self.selected_delivery is None:
            # Check if clicked on a delivery point
            for delivery in deliveries:
                if not delivery['assigned']:
                    dx = delivery['pos'][0] - x
                    dy = delivery['pos'][1] - y
                    if dx*dx + dy*dy < 1:  # Click radius
                        self.selected_delivery = delivery
                        self.status_text.append(f"Selected delivery {delivery['id']}")
                        break
    
    def on_map_motion(self, event):
        """Handle mouse motion for polygon drawing"""
        if event.inaxes != self.ax or not self.drawing_polygon:
            return
            
        if len(self.current_polygon_points) > 0:
            self.update_polygon_preview(event.xdata, event.ydata)
    
    def update_polygon_preview(self, current_x=None, current_y=None):
        """Update the polygon preview while drawing"""
        self.ax.clear()
        plot_map(self.ax, drones, deliveries, no_fly_zones)
        
        points = self.current_polygon_points.copy()
        if current_x is not None and current_y is not None:
            points.append((current_x, current_y))
            
        if len(points) > 1:
            x, y = zip(*points)
            self.ax.plot(x, y, 'r--', alpha=0.5)
            if len(points) > 2:
                self.ax.fill(x, y, 'r', alpha=0.1)
                
        self.canvas.draw()
    
    def start_draw_zone(self):
        """Start drawing a no-fly zone"""
        self.drawing_polygon = True
        self.current_polygon_points = []
        self.status_text.append("Click on the map to draw polygon points. Right-click to finish.")
        
    def finish_draw_zone(self):
        """Finish drawing the no-fly zone and show dialog"""
        if len(self.current_polygon_points) < 3:
            QMessageBox.warning(self, "Error", "Need at least 3 points for a polygon")
            return
            
        dialog = AddNoFlyZoneDialog(self.current_polygon_points, self)
        if dialog.exec_() == QDialog.Accepted:
            zone_data = dialog.get_zone_data()
            no_fly_zones.append(zone_data)
            self.status_text.append(f"Added no-fly zone {zone_data['id']}")
            
        self.drawing_polygon = False
        self.current_polygon_points = []
        self.reset_simulation()
    
    def add_drone(self):
        """Show dialog to add a new drone"""
        dialog = AddDroneDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            drone_data = dialog.get_drone_data()
            drones.append(drone_data)
            self.status_text.append(f"Added drone {drone_data['id']}")
            self.reset_simulation()
    
    def start_add_delivery(self):
        """Start process of adding a delivery by clicking on map"""
        self.status_text.append("Click on the map to place delivery point")
        self.selected_delivery = "new"  # Special marker for new delivery
    
    def add_delivery(self, pos):
        """Show dialog to add a new delivery at the given position"""
        dialog = AddDeliveryDialog(pos, self)
        if dialog.exec_() == QDialog.Accepted:
            delivery_data = dialog.get_delivery_data()
            deliveries.append(delivery_data)
            self.status_text.append(f"Added delivery {delivery_data['id']}")
            self.reset_simulation()
    
    def optimize_routes(self):
        """Run genetic algorithm to optimize routes"""
        self.status_text.append("Optimizing routes...")
        best_route, logbook = optimize_routes(drones, deliveries, no_fly_zones)
        
        # Update delivery order based on optimization
        optimized_deliveries = [deliveries[i] for i in best_route]
        deliveries.clear()
        deliveries.extend(optimized_deliveries)
        
        self.status_text.append("Route optimization complete")
        self.reset_simulation()
    
    def show_statistics(self):
        """Show statistics in the statistics tab"""
        completed = [d for d in deliveries if d['assigned']]
        failed = [d for d in deliveries if not d['assigned'] and 
                 d['time_window'][1] < self.get_current_time_minutes()]
        
        plot_statistics(self.stats_ax, completed, failed, drones)
        self.stats_canvas.draw()
    
    def update_drones_table(self):
        """Update the drones status table"""
        self.drones_table.setRowCount(len(drones))
        for i, drone in enumerate(drones):
            self.drones_table.setItem(i, 0, QTableWidgetItem(str(drone['id'])))
            self.drones_table.setItem(i, 1, QTableWidgetItem(
                f"{drone['battery_left']:.0f}/{drone['battery']:.0f}"
            ))
            self.drones_table.setItem(i, 2, QTableWidgetItem(str(drone['max_weight'])))
            self.drones_table.setItem(i, 3, QTableWidgetItem(
                f"({drone['current_pos'][0]:.1f}, {drone['current_pos'][1]:.1f})"
            ))
            
            status = "Idle"
            if any(d['assigned'] and d.get('drone_id') == drone['id'] for d in deliveries):
                status = "Delivering"
            elif drone['battery_left'] < 20:
                status = "Low Battery"
                
            self.drones_table.setItem(i, 4, QTableWidgetItem(status))
    
    def get_current_time_minutes(self):
        """Get simulation time in minutes (0-120)"""
        try:
            minutes = int(self.time_input.text())
            if 0 <= minutes <= 120:
                return minutes
            else:
                self.status_text.append("Invalid time. Using 0 minutes")
                return 0
        except:
            self.status_text.append("Invalid time format. Using 0 minutes")
            return 0
    
    def reset_simulation(self):
        """Reset the simulation to initial state"""
        try:
            # Stop any running simulation
            self.simulation_timer.stop()
            self.simulation_running = False
            
            # Clear any ongoing animations
            for anim in self.animations:
                anim.event_source.stop()
            self.animations.clear()
            
            # Reset drone states
            for drone in drones:
                drone['current_pos'] = drone['start_pos']
                drone['battery_left'] = drone['battery']
                drone['assigned_delivery'] = None
            
            # Reset delivery states
            for delivery in deliveries:
                delivery['assigned'] = False
                delivery['drone_id'] = None
            
            # Update display
            plot_map(self.ax, drones, deliveries, no_fly_zones)
            self.canvas.draw()
            self.status_text.clear()
            self.update_drones_table()
            
        except Exception as e:
            self.status_text.append(f"Error resetting simulation: {str(e)}")
            self.status_text.append(traceback.format_exc())
    
    def start_simulation(self):
        """Start the delivery simulation"""
        try:
            self.status_text.clear()
            self.simulation_running = True
            
            # Initialize simulation state
            self.current_time = 0
            self.pending_deliveries = deliveries.copy()
            self.active_drones = [drone.copy() for drone in drones]
            self.completed_deliveries = []
            self.failed_deliveries = []
            
            # Reset any existing animations
            for anim in self.animations:
                anim.event_source.stop()
            self.animations.clear()
            
            self.status_text.append(f"Starting simulation at time {self.current_time}")
            
            # Start simulation timer (update every 500ms)
            self.simulation_timer.start(500)
            
        except Exception as e:
            self.status_text.append(f"Error starting simulation: {str(e)}")
            self.status_text.append(traceback.format_exc())
            self.simulation_running = False
    
    def simulation_step(self):
        """Execute one step of the simulation"""
        try:
            if not self.simulation_running or self.current_time > 120:
                self.simulation_timer.stop()
                self.finish_simulation()
                return
            
            # Get available deliveries and drones
            available_deliveries = get_available_deliveries(self.pending_deliveries, self.current_time)
            available_drones = get_available_drones(self.active_drones, self.current_time)
            
            if not available_deliveries and not self.pending_deliveries:
                self.simulation_timer.stop()
                self.finish_simulation()
                return
            
            # Sort deliveries by priority score
            available_deliveries = sort_deliveries_by_priority(available_deliveries, self.current_time)
            
            # Try to assign deliveries
            for delivery in available_deliveries[:]:
                assigned = False
                
                # Find best drone for this delivery
                for drone in available_drones:
                    try:
                        # Basic checks
                        if delivery['weight'] > drone['max_weight']:
                            continue
                        
                        # Calculate path
                        path = astar(drone['current_pos'], delivery['pos'], 
                                    no_fly_zones, delivery['weight'])
                        if not path:
                            continue
                            
                        # Calculate energy needed
                        energy_needed = calculate_energy(path, drone, delivery['weight'])
                        if energy_needed > drone['battery_left']:
                            continue
                        
                        # Assign delivery
                        drone['battery_left'] -= energy_needed
                        drone['assigned_delivery'] = delivery
                        delivery['assigned'] = True
                        delivery['drone_id'] = drone['id']
                        
                        # Animate the delivery
                        anim = animate_drone_path(
                            self.ax, drone, path, delivery, no_fly_zones
                        )
                        if anim:
                            self.animations.append(anim)
                        
                        # Update drone position
                        drone['current_pos'] = delivery['pos']
                        self.pending_deliveries.remove(delivery)
                        self.completed_deliveries.append(delivery)
                        assigned = True
                        
                        # Update display
                        self.status_text.append(
                            f"Time {self.current_time}: Drone {drone['id']} delivering package {delivery['id']}"
                            f" (Priority: {delivery['priority']}, Battery left: {drone['battery_left']:.0f})"
                        )
                        
                        # Update tables and plots
                        self.update_drones_table()
                        plot_map(self.ax, self.active_drones, self.pending_deliveries, 
                                no_fly_zones, self.current_time)
                        self.canvas.draw()
                        QApplication.processEvents()
                        break
                        
                    except Exception as e:
                        self.status_text.append(f"Error processing delivery: {str(e)}")
                        continue
                
                if not assigned:
                    # Check if delivery will expire
                    if self.current_time >= delivery['time_window'][1]:
                        self.pending_deliveries.remove(delivery)
                        self.failed_deliveries.append(delivery)
                        self.status_text.append(
                            f"Time {self.current_time}: Delivery {delivery['id']} failed - Time window expired"
                        )
            
            # Advance time
            self.current_time += 5  # 5-minute intervals
            
        except Exception as e:
            self.status_text.append(f"Error in simulation step: {str(e)}")
            self.status_text.append(traceback.format_exc())
            self.simulation_timer.stop()
            self.simulation_running = False
    
    def finish_simulation(self):
        """Finish the simulation and show final results"""
        try:
            self.simulation_running = False
            
            # Final report
            self.status_text.append("\n=== Final Results ===")
            self.status_text.append(f"Total deliveries: {len(deliveries)}")
            self.status_text.append(f"Completed: {len(self.completed_deliveries)}")
            self.status_text.append(f"Failed: {len(self.failed_deliveries)}")
            
            # Show statistics
            self.show_statistics()
            
            # List failed deliveries
            if self.failed_deliveries:
                self.status_text.append("\nFailed Deliveries:")
                for delivery in self.failed_deliveries:
                    self.status_text.append(
                        f"ID: {delivery['id']}, Priority: {delivery['priority']}, "
                        f"Weight: {delivery['weight']}"
                    )
                    
        except Exception as e:
            self.status_text.append(f"Error finishing simulation: {str(e)}")
            self.status_text.append(traceback.format_exc())

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = DroneSimWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print(traceback.format_exc())

        sys.exit(1)
