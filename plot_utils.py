import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
from matplotlib import transforms
import numpy as np
from matplotlib.animation import FuncAnimation
import matplotlib.colors as mcolors
import time

def create_drone_icon():
    """Create a custom drone icon using matplotlib patches"""
    verts = [
        (0, 0),  # Center
        (-0.5, -0.5),  # Left arm
        (0.5, -0.5),   # Right arm
        (0, -0.8),     # Bottom
        (0, 0.2),      # Top
    ]
    codes = [
        Path.MOVETO,
        Path.LINETO,
        Path.LINETO,
        Path.LINETO,
        Path.LINETO,
    ]
    return Path(verts, codes)

def create_package_icon():
    """Create a custom package icon"""
    verts = [
        (0, 0),      # Bottom left
        (0.4, 0),    # Bottom right
        (0.4, 0.3),  # Top right
        (0, 0.3),    # Top left
        (0, 0),      # Back to start
    ]
    codes = [
        Path.MOVETO,
        Path.LINETO,
        Path.LINETO,
        Path.LINETO,
        Path.CLOSEPOLY,
    ]
    return Path(verts, codes)

def plot_map(ax, drones, deliveries, no_fly_zones, current_time=0):
    """Plot the current state of the simulation"""
    ax.clear()
    
    # Set up the plot
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_title("Drone Delivery Simulation")
    
    # Plot no-fly zones
    for zone in no_fly_zones:
        if zone['time_window'][0] <= current_time <= zone['time_window'][1]:
            polygon = patches.Polygon(
                zone['polygon'],
                facecolor='red',
                alpha=0.3,
                edgecolor='red',
                label='No-Fly Zone'
            )
            ax.add_patch(polygon)
    
    # Plot deliveries
    package_icon = create_package_icon()
    for delivery in deliveries:
        if not delivery['assigned']:
            # Calculate color based on priority (1-5)
            color = plt.cm.RdYlGn((delivery['priority'] - 1) / 4)
            transform = transforms.Affine2D().translate(
                delivery['pos'][0] - 0.2,
                delivery['pos'][1] - 0.15
            ) + ax.transData
            patch = patches.PathPatch(
                package_icon,
                facecolor=color,
                edgecolor='black',
                transform=transform,
                label=f'Delivery {delivery["id"]}'
            )
            ax.add_patch(patch)
            
            # Add weight label
            ax.text(
                delivery['pos'][0],
                delivery['pos'][1] + 0.4,
                f'{delivery["weight"]}kg',
                ha='center',
                va='bottom'
            )
    
    # Plot drones
    drone_icon = create_drone_icon()
    for drone in drones:
        # Calculate battery percentage for color
        battery_pct = drone['battery_left'] / drone['battery']
        color = plt.cm.RdYlGn(battery_pct)
        
        transform = transforms.Affine2D().translate(
            drone['current_pos'][0],
            drone['current_pos'][1]
        ) + ax.transData
        
        patch = patches.PathPatch(
            drone_icon,
            facecolor=color,
            edgecolor='black',
            transform=transform,
            label=f'Drone {drone["id"]}'
        )
        ax.add_patch(patch)
        
        # Add battery and weight capacity labels
        ax.text(
            drone['current_pos'][0],
            drone['current_pos'][1] + 0.4,
            f'B:{drone["battery_left"]:.0f}/{drone["battery"]:.0f}\nW:{drone["max_weight"]}kg',
            ha='center',
            va='bottom',
            fontsize=8
        )
    
    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper right')

def animate_drone_path(ax, drone, path, delivery, no_fly_zones, frames=50):
    """Animate a drone's path to a delivery point"""
    if not path:
        return None
        
    # Create initial plot
    plot_map(ax, [drone], [delivery], no_fly_zones)
    
    # Create animation
    def update(frame):
        ax.clear()
        plot_map(ax, [drone], [delivery], no_fly_zones)
        
        # Calculate current position
        idx = int(frame * (len(path) - 1) / (frames - 1))
        current_pos = path[idx]
        
        # Update drone position
        drone['current_pos'] = current_pos
        
        # Draw path up to current position
        path_x = [p[0] for p in path[:idx+1]]
        path_y = [p[1] for p in path[:idx+1]]
        ax.plot(path_x, path_y, 'b--', alpha=0.5)
        
        return ax,
    
    anim = FuncAnimation(
        ax.figure,
        update,
        frames=frames,
        interval=50,
        blit=True
    )
    
    return anim

def plot_statistics(ax, completed_deliveries, failed_deliveries, drone_stats):
    """Plot statistics in a separate figure"""
    # Clear the current figure
    ax.figure.clear()
    
    # Create a new GridSpec
    gs = ax.figure.add_gridspec(2, 2)
    
    # Create subplots
    ax1 = ax.figure.add_subplot(gs[0, 0])  # Delivery success rate
    ax2 = ax.figure.add_subplot(gs[0, 1])  # Battery usage
    ax3 = ax.figure.add_subplot(gs[1, :])  # Priority distribution
    
    # Plot delivery success/failure
    labels = ['Completed', 'Failed']
    sizes = [len(completed_deliveries), len(failed_deliveries)]
    if sum(sizes) > 0:  # Only plot if there are deliveries
        ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['green', 'red'])
    ax1.set_title('Delivery Success Rate')
    
    # Plot drone battery usage
    if drone_stats:  # Only plot if there are drones
        drone_ids = [d['id'] for d in drone_stats]
        battery_used = [d['battery'] - d['battery_left'] for d in drone_stats]
        ax2.bar(drone_ids, battery_used)
        ax2.set_title('Battery Usage per Drone')
        ax2.set_xlabel('Drone ID')
        ax2.set_ylabel('Battery Used')
    
    # Plot delivery priorities
    all_deliveries = completed_deliveries + failed_deliveries
    if all_deliveries:  # Only plot if there are deliveries
        priorities = [d['priority'] for d in all_deliveries]
        ax3.hist(priorities, bins=5, range=(1, 6), rwidth=0.8)
        ax3.set_title('Delivery Priority Distribution')
        ax3.set_xlabel('Priority (1-5)')
        ax3.set_ylabel('Number of Deliveries')
    
    ax.figure.tight_layout()