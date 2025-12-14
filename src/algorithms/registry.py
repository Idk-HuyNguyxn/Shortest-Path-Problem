from algorithms.astar import astar
from algorithms.dijkstra import dijkstra

ALGORITHMS = {
    "astar": {
        "func": astar,
        "returns_distance": False
    },
    "dijkstra": {
        "func": dijkstra,
        "returns_distance": True
    }
}
