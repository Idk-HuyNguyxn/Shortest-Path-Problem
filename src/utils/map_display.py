import folium
import sqlite3

#load edges, nodes tu DataBase

conn = sqlite3.connect("map_data.db")
c = conn.cursor()

#Lay Nodes
c.execute("SELECT id, lat, lon FROM nodes")
nodes = {row[0]: (row[1], row[2]) for row in c.fetchall() } #lay toan bo dong va tra ve dang list id : (lat, lon)

#lay Edges
c.execute("SELECT from_node, to_node FROM edges")
edges = c.fetchall()

conn.close()


#Tao map folium

if nodes:
    avg_lat = sum(lat for lat, lon in nodes.values()) / len(nodes) # lat trung binh
    avg_lon = sum(lon for lat, lon in nodes.values()) / len(nodes) # lon trung binh
else:
    avg_lat, avg_lon = 0.0
    
m = folium.Map(location = [avg_lat, avg_lon], zoom_start= 14 )

#Ve cac duong
for from_node, to_node in edges:
    if from_node in nodes and to_node in nodes:
        folium.PolyLine([nodes[from_node], nodes[to_node]], color = " blue ", weight = 1 ).add_to(m)
        
m.save("map.html")
print("Map saved as map.html")