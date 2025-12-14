# src/main.py
from utils.map_handler import build_graph, get_all_nodes, get_all_edges
from algorithms import AStar, dijkstra

def main():
    print("Loading graph from database...")
    nodes = get_all_nodes()
    edges = get_all_edges()
    graph = build_graph(nodes, edges)

    print("Graph loaded!")
    print("Total nodes:", len(graph))
if __name__ == "__main__":
    main()
