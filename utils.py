import math
import heapq
from shapely.geometry import LineString, Polygon

def calculate_distance(p1, p2):
    """Calculate Euclidean distance between two points"""
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5

def assign_drones_to_deliveries(drones, deliveries):
    assignments = {}
    sorted_deliveries = sorted(deliveries, key=lambda d: d['priority'], reverse=True)
    for delivery in sorted_deliveries:
        for drone in drones:
            if drone['max_weight'] >= delivery['weight']:
                if drone['id'] not in assignments:
                    assignments[drone['id']] = delivery
                    break
    return assignments

def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0]
    for i in range(n+1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y)*(p2x - p1x)/(p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def line_intersects_polygon(p1, p2, polygon):
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

    def segments_intersect(A, B, C, D):
        return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

    n = len(polygon)
    for i in range(n):
        poly_p1 = polygon[i]
        poly_p2 = polygon[(i+1) % n]
        if segments_intersect(p1, p2, poly_p1, poly_p2):
            return True
    return False

def intersects_no_fly_zone(p1, p2, no_fly_zones, current_time):
    for zone in no_fly_zones:
        start_time, end_time = zone['active_time']
        if not (start_time <= current_time <= end_time):
            continue
        polygon = zone['coordinates']
        if line_intersects_polygon(p1, p2, polygon):
            return True
    return False

def astar(start, goal, no_fly_zones, current_time=0):
    if intersects_no_fly_zone(start, goal, no_fly_zones, current_time):
        return None
    return [start, goal]

def calculate_energy(path, drone, package_weight=0):
    """Calculate energy consumption for a path"""
    if not path or len(path) < 2:
        return 0
    
    # Base energy consumption per unit distance
    base_energy = 10
    
    # Energy multiplier based on package weight
    weight_factor = 1 + (package_weight / drone['max_weight'])
    
    # Speed factor (faster drones consume more energy)
    speed_factor = 1 + (drone['speed'] / 10)
    
    total_energy = 0
    for i in range(len(path)-1):
        distance = calculate_distance(path[i], path[i+1])
        # Energy consumption increases with distance, weight, and speed
        segment_energy = distance * base_energy * weight_factor * speed_factor
        total_energy += segment_energy
    
    return total_energy

def check_time_window(current_time, delivery):
    """Check if a delivery is within its time window"""
    start, end = delivery['time_window']
    return start <= current_time <= end

def is_drone_available(drone, current_time, current_delivery=None):
    """Check if a drone is available for a new delivery"""
    # Check battery level
    if drone['battery_left'] < 1000:  # Minimum battery threshold
        return False
    
    # If drone is currently assigned, check if it can take another delivery
    if current_delivery and drone['assigned_delivery']:
        return False
    
    return True

def get_available_drones(drones, current_time):
    """Get list of drones available for new deliveries"""
    return [drone for drone in drones if is_drone_available(drone, current_time)]

def get_available_deliveries(deliveries, current_time):
    """Get list of deliveries available at current time"""
    return [d for d in deliveries if check_time_window(current_time, d) and not d['assigned']]

def calculate_delivery_score(delivery, current_time):
    """Calculate a score for delivery priority based on multiple factors"""
    # Time urgency (higher score for deliveries closer to their deadline)
    time_left = delivery['time_window'][1] - current_time
    time_urgency = 1 / (time_left + 1)  # Add 1 to avoid division by zero
    
    # Priority factor (1-5)
    priority_factor = delivery['priority'] / 5
    
    # Weight factor (normalized by max weight)
    weight_factor = delivery['weight'] / 6.0  # Assuming max weight is 6.0
    
    # Combine factors (you can adjust weights)
    score = (priority_factor * 0.5 + time_urgency * 0.3 + weight_factor * 0.2)
    
    return score

def sort_deliveries_by_priority(deliveries, current_time):
    """Sort deliveries by their priority score"""
    return sorted(
        deliveries,
        key=lambda d: calculate_delivery_score(d, current_time),
        reverse=True
    )
