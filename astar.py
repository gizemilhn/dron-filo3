import heapq
from shapely.geometry import LineString, Polygon

def heuristic(a, b):
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2)**0.5

def intersects_no_fly_zone(p1, p2, no_fly_zones):
    line = LineString([p1, p2])
    for zone in no_fly_zones:
        poly = Polygon(zone["polygon"])
        if line.crosses(poly) or line.within(poly) or line.intersects(poly):
            return True
    return False

def astar(start, goal, no_fly_zones, weight):
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    step_size = 5  # adım büyüklüğü

    while open_set:
        current = heapq.heappop(open_set)[1]
        if heuristic(current, goal) < step_size:
            # hedefe yaklaştık
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return path

        for dx in [-step_size, 0, step_size]:
            for dy in [-step_size, 0, step_size]:
                if dx == 0 and dy == 0:
                    continue
                neighbor = (current[0] + dx, current[1] + dy)
                tentative_g = g_score[current] + heuristic(current, neighbor)

                if intersects_no_fly_zone(current, neighbor, no_fly_zones):
                    continue

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return None
