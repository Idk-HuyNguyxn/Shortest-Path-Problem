import folium
import sqlite3

#load edges, nodes tu DataBase

conn = sqlite3.connect("map_data.db")
c = conn.cursor()

#Lay Nodes
c.execute("SELECT id, lat, lon FROM nodes")
nodes = {row[0]: (row[1], row[2]) for row in c.fetchall() } #lay toan bo dong va tra ve dang list id : (lat, lon)

#lay Edges
c.execute("SELECT from_node, to_node, status FROM edges")
edges = c.fetchall()

conn.close()


#Tao map folium

if nodes:
    avg_lat = sum(lat for lat, lon in nodes.values()) / len(nodes) # lat trung binh
    avg_lon = sum(lon for lat, lon in nodes.values()) / len(nodes) # lon trung binh
else:
    avg_lat =  21.0357879
    avg_lon = 105.8276413
    
m = folium.Map(location = [avg_lat, avg_lon], zoom_start= 15 )

#Ve cac duong
for from_node, to_node, status in edges:
    if from_node in nodes and to_node in nodes:
        if status == "normal": color = "blue"
        elif status == "block": color = "red"
        else: color = "orange"
        folium.PolyLine(
            [ nodes[from_node], nodes[to_node] ],
            color = color,
            weight = 1
        ).add_to(m)
        
m.save("map.html")
print("Map saved as map.html")