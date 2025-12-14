import sys
import os
import tempfile

# ------------------ Đường dẫn utils ------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))   # src/Main
SRC_ROOT = os.path.dirname(CURRENT_DIR)                    # src
sys.path.insert(0, SRC_ROOT)

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QInputDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QObject, pyqtSlot, QUrl
from PyQt5.QtWebChannel import QWebChannel
from utils.map_handler import load_graph_from_db, get_map_center, set_edge_status, get_all_edges

MAP_HTML = os.path.join(tempfile.gettempdir(), "admin_map.html")

STATUS_COLOR = {
    "normal": "gray",
    "traffic": "orange",
    "flood": "blue",
    "block": "red"
}

# ---------------- JS Bridge ----------------
class JsBridge(QObject):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui

    @pyqtSlot(float, float)
    def onMapClick(self, lat, lon):
        self.gui.map_click(lat, lon)

# ---------------- AdminGUI ----------------
class AdminGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Map Viewer")
        self.resize(1000, 700)

        # Load nodes & edges
        self.graph, self.nodes = load_graph_from_db()
        self.edges = get_all_edges()

        # Layout
        layout = QVBoxLayout(self)
        btn_layout = QHBoxLayout()
        self.edge_btn = QPushButton("Edge Mode")
        self.edge_btn.clicked.connect(lambda: self.set_mode("edge"))
        self.poly_btn = QPushButton("Polygon Mode")
        self.poly_btn.clicked.connect(lambda: self.set_mode("polygon"))
        self.finish_poly_btn = QPushButton("Finish Polygon")
        self.finish_poly_btn.clicked.connect(self.finish_polygon)

        btn_layout.addWidget(self.edge_btn)
        btn_layout.addWidget(self.poly_btn)
        btn_layout.addWidget(self.finish_poly_btn)
        layout.addLayout(btn_layout)

        # Web view
        self.web = QWebEngineView()
        layout.addWidget(self.web)

        # Mode & polygon storage
        self.mode = "edge"
        self.poly_edges = []            # edges đang chọn polygon
        self.highlight_edges_list = []  # edges highlight tạm

        # JS bridge
        self.channel = QWebChannel()
        self.js_bridge = JsBridge(self)
        self.channel.registerObject("pyHandler", self.js_bridge)
        self.web.page().setWebChannel(self.channel)

        # Initial map
        lat_avg, lon_avg = get_map_center()
        self.create_map(lat_avg, lon_avg)
        self.web.load(QUrl.fromLocalFile(MAP_HTML))
        self.web.loadFinished.connect(self.inject_js)

    # ---------------- Map ----------------
    def create_map(self, lat, lon):
        import folium
        m = folium.Map(location=(lat, lon), zoom_start=17)

        # Nodes
        for nid, (nlat, nlon) in self.nodes.items():
            folium.CircleMarker(
                location=(nlat, nlon),
                radius=3,
                color="blue",
                fill=True,
                fill_opacity=0.7,
                tooltip=f"Node {nid}"
            ).add_to(m)

        # Edges
        for e in self.edges:
            u, v = e["u"], e["v"]
            if u in self.nodes and v in self.nodes:
                lat1, lon1 = self.nodes[u]
                lat2, lon2 = self.nodes[v]
                color = STATUS_COLOR.get(e.get("status", "normal"), "gray")
                folium.PolyLine(
                    [(lat1, lon1), (lat2, lon2)],
                    color=color,
                    weight=3,
                    opacity=0.7,
                    tooltip=f"Edge {u}-{v} | {e.get('status','normal')}"
                ).add_to(m)

        # JS
        m.get_root().header.add_child(folium.Element("""
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        """))
        m.save(MAP_HTML)

    # ---------------- Inject JS ----------------
    def inject_js(self):
        js = r"""
        (function() {
            function waitForTransport(cb) {
                if (typeof qt !== 'undefined' && qt.webChannelTransport) return cb();
                setTimeout(function(){ waitForTransport(cb); }, 50);
            }

            waitForTransport(function() {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.pyHandler = channel.objects.pyHandler;
                    function attachClick() {
                        let keys = Object.keys(window).filter(k => k.startsWith("map_"));
                        if (keys.length === 0) { setTimeout(attachClick, 50); return; }
                        let mapObj = window[keys[0]];
                        if (!mapObj._py_click_attached) {
                            mapObj._py_click_attached = true;
                            mapObj.on('click', function(e) {
                                pyHandler.onMapClick(e.latlng.lat, e.latlng.lng);
                            });
                        }
                    }
                    attachClick();
                });
            });
        })();
        """
        self.web.page().runJavaScript(js)

    # ---------------- Mode ----------------
    def set_mode(self, mode):
        self.mode = mode
        self.poly_edges.clear()
        self.highlight_edges_list.clear()
        QMessageBox.information(self, "Mode Changed", f"Current mode: {mode}")

    # ---------------- Map click ----------------
    def map_click(self, lat, lon):
        if self.mode == "edge":
            self.select_edge(lat, lon)
        elif self.mode == "polygon":
            self.toggle_polygon_edge(lat, lon)

    # ---------------- Edge Mode ----------------
    def select_edge(self, lat, lon):
        edge = self.nearest_edge(lat, lon)
        if not edge:
            QMessageBox.information(self, "No edge", "Click is not close to any edge")
            return
        statuses = ["normal", "traffic", "flood", "block"]
        status, ok = QInputDialog.getItem(self, f"Edge {edge['u']}-{edge['v']}", "Set status:", statuses, 0, False)
        if ok:
            edge["status"] = status
            set_edge_status(edge["edge_id"], status)
            self.update_edge_color(edge, status)

    # ---------------- Polygon Mode ----------------
    def toggle_polygon_edge(self, lat, lon):
        edge = self.nearest_edge(lat, lon)
        if not edge:
            return
        if edge in self.poly_edges:
            # Bỏ chọn
            self.poly_edges.remove(edge)
            self.highlight_edges_list.remove(edge)
            self.update_edge_color(edge, edge["status"])
        else:
            # Chọn
            self.poly_edges.append(edge)
            self.highlight_edges_list.append(edge)
            self.update_edge_color(edge, "green")

    def finish_polygon(self):
        if not self.poly_edges:
            QMessageBox.information(self, "Polygon", "No edges selected")
            return

        statuses = ["normal", "traffic", "flood", "block"]
        status, ok = QInputDialog.getItem(
            self, "Polygon", "Set status for all edges:", statuses, 0, False
        )
        if not ok:
            return

        self.highlight_edges_list.clear()

        for e in self.poly_edges:
            e["status"] = status
            set_edge_status(e["edge_id"], status)
            self.update_edge_color(e, status)

        self.poly_edges.clear()

    # ---------------- Update edge color ----------------
    def update_edge_color(self, edge, status):
        u, v = edge["u"], edge["v"]
        lat1, lon1 = self.nodes[u]
        lat2, lon2 = self.nodes[v]
        if edge in self.highlight_edges_list:
            color = "green"
        else:
            color = STATUS_COLOR.get(status, "gray")

        js = f"""
        (function(){{
            let keys = Object.keys(window).filter(k => k.startsWith("map_"));
            if(keys.length>0){{
                let mapObj = window[keys[0]];
                mapObj.eachLayer(function(layer){{
                    if(layer instanceof L.Polyline){{
                        let latlngs = layer.getLatLngs();
                        if(latlngs.length==2 &&
                            latlngs[0].lat=={lat1} && latlngs[0].lng=={lon1} &&
                            latlngs[1].lat=={lat2} && latlngs[1].lng=={lon2}){{
                                layer.setStyle({{color:"{color}"}});
                        }}
                    }}
                }});
            }}
        }})();
        """
        self.web.page().runJavaScript(js)

    # ---------------- Nearest edge ----------------
    def nearest_edge(self, lat, lon):
        best_edge = None
        best_dist = 1e18
        for e in self.edges:
            u, v = e["u"], e["v"]
            lat1, lon1 = self.nodes[u]
            lat2, lon2 = self.nodes[v]
            dx, dy = lat2 - lat1, lon2 - lon1
            if dx == dy == 0:
                dist = (lat - lat1)**2 + (lon - lon1)**2
            else:
                t = max(0, min(1, ((lat - lat1)*dx + (lon - lon1)*dy)/(dx*dx + dy*dy)))
                proj_lat = lat1 + t*dx
                proj_lon = lon1 + t*dy
                dist = (lat - proj_lat)**2 + (lon - proj_lon)**2
            if dist < best_dist:
                best_dist = dist
                best_edge = e
        return best_edge

# ---------------- Main ----------------
def main():
    app = QApplication(sys.argv)
    gui = AdminGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
