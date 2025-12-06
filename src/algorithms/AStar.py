import heapq
from .heuristic import haversine
from typing import Dict, List, Tuple, Any
INF = float("inf")

def AStar(
    graph: Dict[Any, List[Tuple[Any, float]]],
    nodes: Dict[Any, Tuple[float, float]],
    start: float,
    goal: float
):
    g = {n : INF for n in graph}
    g[start] = 0
    pq = []
    heapq.heappush(pq, (0, start))
    
    came_from = {}
    
    while pq:
        f_curr, current = heapq.heappop(pq)
        
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            return path[::-1]
        for neighbor, weight in graph[current]:
            tentative_g = g[current] + weight
            if tentative_g < g[neighbor]:
                came_from[neighbor] = current
                g[neighbor] = tentative_g
                
                #heuristic tu neigh -> goal
                h = haversine(nodes, neighbor, goal)
                f = tentative_g + h
                
                heapq.heappush(pq, (f, neighbor))
    return None