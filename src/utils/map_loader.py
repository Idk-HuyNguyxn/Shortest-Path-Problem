import osmnx as ox
import networkx as nx 
import sqlite3
import os

# load file osm
osm_file = "../../map.osm" #dinh nghia ten file osm
graph = ox.graph_from_xml(osm_file) #doc file
print(f"Graph loaded:  {len(graph.nodes)} nodes, {len(graph.edges)} edges ") # in ra so luong nodes va edges da load
if not nx.is_connected(graph.to_undirected()): #is_connect hoat dong voi do thi vo huong ->  undirected chuyen thanh vo huong roi kiem tra lien thong
    largest_cc_nodes = max(nx.connected_components(graph.to_undirected()), key=len) 
    #nx.connected_components(G) tra ve 1 list tap node, moi tap hop la 1 thanh phan lien thong, max -> chon ra tap lien thong lon nhat
    graph = graph.subgraph(largest_cc_nodes).copy()
print(f"Largest component: {len(graph.nodes)} nodes, {len(graph.edges)} edges")


#Luu nodes, edges vao DB SQLite3
db_path = os.path.abspath("map_data.db")
print(f"Database path: {db_path}")
conn = sqlite3.connect("map_data.db") #ket noi toi db map_data.db ( neu chua ton tai thi se tao file db )
c = conn.cursor() #tao cursor c de thuc hien lenh SQL

# #xoa DB truoc
c.execute("DROP TABLE IF EXISTS edges")
c.execute("DROP TABLE IF EXISTS nodes")
#tao DB Nodes
c.execute('''
CREATE TABLE IF NOT EXISTS nodes( 
    id INTEGER PRIMARY KEY,
    lat REAL,
    lon REAL
    )
''')

#tao DB edges
c.execute('''
CREATE TABLE IF NOT EXISTS edges(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_node INTEGER,
    to_node INTEGER,
    length REAL,
    oneway INTEGER,
    status TEXT DEFAULT 'normal',
    FOREIGN KEY(from_node) REFERENCES nodes(id),
    FOREIGN KEY(to_node) REFERENCES nodes(id)
)
''')

#luu nodes
for node_id, data in graph.nodes(data = True):
    c.execute( "INSERT OR IGNORE INTO nodes (id, lat, lon) VALUES (?, ?, ?)", (node_id, data['y'], data['x']) )
#luu edges
for u, v, data in graph.edges(data = True):
    length = data.get('length', 0)
    c.execute( "INSERT INTO edges (from_node, to_node, length, oneway) VALUES (?, ?, ?, ?)", (
        u, v,
        data.get("length", 0),
        int(data.get("oneway", 0)) if data.get("oneway") is not None else 0
    ))
conn.commit()
conn.close()
print("Database saved: map_data.db")