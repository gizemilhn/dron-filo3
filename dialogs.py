from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QTimeEdit, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt, QTime
from datetime import datetime, time

class AddDroneDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Drone")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        
        # Drone ID
        self.id_input = QLineEdit()
        layout.addRow("Drone ID:", self.id_input)
        
        # Start position
        pos_layout = QHBoxLayout()
        self.x_input = QDoubleSpinBox()
        self.y_input = QDoubleSpinBox()
        self.x_input.setRange(0, 100)
        self.y_input.setRange(0, 100)
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.x_input)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.y_input)
        layout.addRow("Start Position:", pos_layout)
        
        # Battery capacity
        self.battery_input = QDoubleSpinBox()
        self.battery_input.setRange(0, 1000)
        self.battery_input.setValue(100)
        layout.addRow("Battery Capacity:", self.battery_input)
        
        # Max weight
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0, 100)
        self.weight_input.setValue(10)
        layout.addRow("Max Weight (kg):", self.weight_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)
        
    def get_drone_data(self):
        return {
            'id': self.id_input.text(),
            'start_pos': (self.x_input.value(), self.y_input.value()),
            'battery': self.battery_input.value(),
            'max_weight': self.weight_input.value(),
            'current_pos': (self.x_input.value(), self.y_input.value()),
            'battery_left': self.battery_input.value()
        }

class AddDeliveryDialog(QDialog):
    def __init__(self, pos=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Delivery")
        self.pos = pos
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        
        # Delivery ID
        self.id_input = QLineEdit()
        layout.addRow("Delivery ID:", self.id_input)
        
        # Position
        pos_layout = QHBoxLayout()
        self.x_input = QDoubleSpinBox()
        self.y_input = QDoubleSpinBox()
        self.x_input.setRange(0, 100)
        self.y_input.setRange(0, 100)
        if self.pos:
            self.x_input.setValue(self.pos[0])
            self.y_input.setValue(self.pos[1])
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.x_input)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.y_input)
        layout.addRow("Position:", pos_layout)
        
        # Weight
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0, 100)
        self.weight_input.setValue(5)
        layout.addRow("Weight (kg):", self.weight_input)
        
        # Priority
        self.priority_input = QSpinBox()
        self.priority_input.setRange(1, 5)
        self.priority_input.setValue(3)
        layout.addRow("Priority (1-5):", self.priority_input)
        
        # Time window
        time_layout = QHBoxLayout()
        self.start_time = QTimeEdit()
        self.end_time = QTimeEdit()
        self.start_time.setTime(QTime(0, 0))
        self.end_time.setTime(QTime(2, 0))
        time_layout.addWidget(QLabel("Start:"))
        time_layout.addWidget(self.start_time)
        time_layout.addWidget(QLabel("End:"))
        time_layout.addWidget(self.end_time)
        layout.addRow("Time Window:", time_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)
        
    def get_delivery_data(self):
        start_time = self.start_time.time()
        end_time = self.end_time.time()
        
        return {
            'id': self.id_input.text(),
            'pos': (self.x_input.value(), self.y_input.value()),
            'weight': self.weight_input.value(),
            'priority': self.priority_input.value(),
            'time_window': (
                start_time.hour() * 60 + start_time.minute(),
                end_time.hour() * 60 + end_time.minute()
            ),
            'assigned': False
        }

class AddNoFlyZoneDialog(QDialog):
    def __init__(self, polygon=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add No-Fly Zone")
        self.polygon = polygon
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        
        # Zone ID
        self.id_input = QLineEdit()
        layout.addRow("Zone ID:", self.id_input)
        
        # Time window
        time_layout = QHBoxLayout()
        self.start_time = QTimeEdit()
        self.end_time = QTimeEdit()
        self.start_time.setTime(QTime(0, 0))
        self.end_time.setTime(QTime(2, 0))
        time_layout.addWidget(QLabel("Start:"))
        time_layout.addWidget(self.start_time)
        time_layout.addWidget(QLabel("End:"))
        time_layout.addWidget(self.end_time)
        layout.addRow("Active Time Window:", time_layout)
        
        # Note about polygon
        if self.polygon:
            layout.addRow(QLabel("Polygon coordinates will be used from the map."))
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)
        
    def get_zone_data(self):
        start_time = self.start_time.time()
        end_time = self.end_time.time()
        
        return {
            'id': self.id_input.text(),
            'polygon': self.polygon,
            'time_window': (
                start_time.hour() * 60 + start_time.minute(),
                end_time.hour() * 60 + end_time.minute()
            )
        } 