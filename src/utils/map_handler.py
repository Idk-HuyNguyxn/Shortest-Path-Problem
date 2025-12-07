import sqlite3
import os
from typing import Dict, Tuple, List, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "map_data.db")
#lay toan bo nodes tu DB va tra ve dict: {id : (lat, lon)}
def get_all_nodes(db_path: str = DB_PATH) -> Dict[int, Tuple[float, float]]:
    #tra ve dang dict: {node_id : (lat, lon)}
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT id, lat, lon FROM nodes")
        rows = c.fetchall()
    nodes = {row[0] : (row[1], row[2]) for row in rows}
    conn.close()
    return nodes

#lay toan bo edges tu DB va tra ve list cac dict
def get_all_edges(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
# tra ve dang list cac dict co dang { "edge_id", "u", "v", "length", "oneway", "status" }
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, from_node, to_node, length, oneway, status FROM edges"
        )
        rows = c.fetchall()

    edges: List[Dict[str, Any]] = []
    for row in rows:
        edge_id, from_node, to_node, length, oneway, status = row
        edges.append({
            "edge_id": edge_id,
            "u": from_node,
            "v": to_node,
            "length": float(length) if length is not None else 0.0,
            "oneway": int(oneway) if oneway is not None else 0,
            "status": status
        })
    return edges


def get_edge_status(edge_id: int, db_path: str = DB_PATH) -> Any:
#tra ve status ( None neu khong thay )
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT status FROM edges WHERE id = ? LIMIT 1", (edge_id,))
        row = c.fetchone()
    return row[0] if row else None


def set_edge_status(edge_id: int, status: str, db_path: str = DB_PATH) -> None:
#cap nhap status ( dung trong admin )
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("UPDATE edges SET status = ? WHERE id = ?", (status, edge_id))
        conn.commit()


def build_graph(nodes: Dict[int, Tuple[float, float]],
                edges: List[Dict[str, Any]]) -> Dict[int, List[Tuple[int, float]]]:
#tao ds ke graph: graph[node_id] = [(neighbor_id, length), ...]
    # nodes: {id: (lat, lon)} -> key la node_id
    graph: Dict[int, List[Tuple[int, float]]] = {node_id: [] for node_id in nodes}

    for e in edges:
        if e["status"] == "block":
            continue

        u = e["u"]
        v = e["v"]
        w = float(e.get("length", 0.0))

        if u not in graph or v not in graph:
            continue

        graph[u].append((v, w))
        if int(e.get("oneway", 0)) == 0:
            graph[v].append((u, w))
    return graph


def load_graph_from_db(db_path: str = DB_PATH):
#load nodes, edges tu DB va build graph, tra ve graph: {node_id : [(neighbor, len), ...]} va coords: {node_id: (lat, lon)}
    nodes = get_all_nodes(db_path)
    edges = get_all_edges(db_path)
    graph = build_graph(nodes, edges)
    return graph, nodes

def get_map_center():
    nodes = get_all_nodes()
    if not nodes:
        return  21.0357, 105.8276

    lats = [lat for (lat, lon) in nodes.values()]
    lons = [lon for (lat, lon) in nodes.values()]
    return sum(lats)/len(lats), sum(lons)/len(lons)

    