# src/main.py
from utils.map_handler import build_graph, get_all_nodes, get_all_edges
from algorithms import astar, dijkstra

def main():
    print("Loading graph from database...")
    nodes = get_all_nodes()
    edges = get_all_edges()
    graph = build_graph(nodes, edges)

    print("Graph loaded!")
    print("Total nodes:", len(graph))

    # --- TEST 1: A* ---
    start = 1
    goal = 10
    print("\n=== A* SEARCH ===")
    path = AStar(graph, nodes, start, goal)
    print("A* Path:", path)

    # --- TEST 2: Dijkstra ---
    print("\n=== DIJKSTRA ===")
    path2, dist2 = Dijkstra(graph, nodes, start, goal)
    print("Dijkstra Path:", path2)
    print("Distance:", dist2)

if __name__ == "__main__":
    main()
