import math
from typing import Dict, Tuple, List, Any
import heapq
def dijkstra(
    graph: Dict[Any, List[Tuple[Any, float]]],
    nodes: Dict[Any, Tuple[float, float]],
    start: Any,
    goal: Any
):
    pq = []
    heapq.heappush(pq, (0, start))
    dist = {n : float("inf") for n in graph}
    dist[start] = 0
    parent = {start: None}
    while pq:
        cur_cost, u = heapq.heappop(pq)
        if u == goal:
            break
        if cur_cost > dist[u]:
            continue
        
        for v, length in graph[u]:
            new_cost = cur_cost + length
            if new_cost < dist[v]:
                dist[v] = new_cost
                parent[v] = u
                heapq.heappush(pq, (new_cost, v))
    if goal not in parent:
        return None, float("inf")
    path = []
    node = goal
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()
    return path, dist[goal]