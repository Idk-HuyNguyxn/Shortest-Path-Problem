import sqlite3

DB_path = "map_data.db"

def get_all_nodes():
    conn = sqlite3
    c = conn.cursor()
    c.execute("SELECT id, lat, lon FROM nodes")
    nodes = {row[0] : (row[1], row[2]) for row in c.fetchall()}
    conn.close()
    return nodes

def get_all_edges():
    conn = sqlite3
    c = conn.cursor()
    c.execute("SELECT id, from_node, to_node, status FROM edges")
    edges = [{"id" : row[0], "from": row[1], "to": row[2], "status": row[3] } for row in c.fetchall()]
    conn.close()
    return edges

def get_edge_status(edge_id):
    conn = sqlite3.connect(DB_path)
    c = conn.cursor()
    c.execute("SELECT status FROM edges WHERE id = ? ", (edge_id))
    status = c.fetchone()[0]
    conn.close()
    return status

def set_edge_status(edge_id, status):
    conn = sqlite3.connect(DB_path)
    c = conn.cursor()
    c.execute("UPDATE edges SET status = ?  WHERE id = ? " (status, edge_id))
    conn.comit()
    conn.close()