import sys
import os
import tempfile
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QMessageBox, QInputDialog, QPushButton, QHBoxLayout
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QObject, pyqtSlot, QUrl
from PyQt5.QtWebChannel import QWebChannel

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, SRC_ROOT)

from utils.map_handler import load_graph_from_db, get_map_center, get_all_edges, set_edge_status

import folium

MAP_HTML = os.path.join(tempfile.gettempdir(), "admin_map.html")

STATUS_COLOR = {
    "normal": "gray",
    "traffic": "orange",
    "flood": "blue",
    "block": "red"
}


class JsBridge(QObject):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui

    @pyqtSlot(float, float)
    def onMapClick(self, lat, lon):
        self.gui.map_click(lat, lon)


class AdminGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Map Viewer")
        self.resize(1200, 800)

        # Load nodes + edges
        self.graph, self.nodes = load_graph_from_db()
        self.edges = [
            {"edge_id": e["edge_id"], "u": e["u"], "v": e["v"], "status": e.get("status", "normal")}
            for e in get_all_edges()
        ]

        self.selected_edges = []  # dùng cho polygon mode
        self.mode = "edge"  # edge hoặc polygon

        # Layout
        main_layout = QVBoxLayout(self)
        btn_layout = QHBoxLayout()

        self.btn_mode = QPushButton("Switch to Polygon Mode")
        self.btn_mode.clicked.connect(self.toggle_mode)
        btn_layout.addWidget(self.btn_mode)

        main_layout.addLayout(btn_layout)

        self.web = QWebEngineView()
        main_layout.addWidget(self.web)

        # JS bridge
        self.channel = QWebChannel()
        self.js_bridge = JsBridge(self)
        self.channel.registerObject("pyHandler", self.js_bridge)
        self.web.page().setWebChannel(self.channel)

        # Create initial map
        lat_avg, lon_avg = get_map_center()
        self.create_map(lat_avg, lon_avg)

        # Load HTML
        self.web.load(QUrl.fromLocalFile(MAP_HTML))
        self.web.loadFinished.connect(self.inject_js)

    # ------------------ Toggle Mode ------------------
    def toggle_mode(self):
        if self.mode == "edge":
            self.mode = "polygon"
            self.btn_mode.setText("Switch to Edge Mode")
            self.selected_edges = []
        else:
            self.mode = "edge"
            self.btn_mode.setText("Switch to Polygon Mode")
            self.selected_edges = []
        QMessageBox.information(self, "Mode switched", f"Current mode: {self.mode}")

    # ------------------ Map ------------------
    def create_map(self, lat, lon):
        m = folium.Map(location=(lat, lon), zoom_start=17)
        for nid, (nlat, nlon) in self.nodes.items():
            folium.CircleMarker(
                location=(nlat, nlon),
                radius=3,
                color="blue",
                fill=True,
                fill_opacity=0.7,
                tooltip=f"Node {nid}"
            ).add_to(m)

        # Vẽ edges theo trạng thái
        for e in self.edges:
            u, v, status = e["u"], e["v"], e["status"]
            if u in self.nodes and v in self.nodes:
                lat1, lon1 = self.nodes[u]
                lat2, lon2 = self.nodes[v]
                folium.PolyLine(
                    [(lat1, lon1), (lat2, lon2)],
                    color=STATUS_COLOR.get(status, "gray"),
                    weight=3,
                    opacity=0.7,
                    tooltip=f"Edge {u}-{v} | {status}"
                ).add_to(m)

        # Chèn QWebChannel JS
        m.get_root().header.add_child(folium.Element("""
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        """))

        m.save(MAP_HTML)

    # ------------------ Inject JS ------------------
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

    # ------------------ Click Map ------------------
    def map_click(self, lat, lon):
        edge = self.nearest_edge(lat, lon)
        if not edge:
            QMessageBox.information(self, "No edge", "Click is not close to any edge")
            return

        if self.mode == "edge":
            self.set_edge(edge)
        elif self.mode == "polygon":
            if edge not in self.selected_edges:
                self.selected_edges.append(edge)
                self.highlight_edge(edge)

    # ------------------ Nearest Edge ------------------
    def nearest_edge(self, lat, lon):
        best_edge = None
        best_dist = 1e18
        for e in self.edges:
            u, v = e["u"], e["v"]
            if u not in self.nodes or v not in self.nodes:
                continue
            lat1, lon1 = self.nodes[u]
            lat2, lon2 = self.nodes[v]
            # Khoảng cách điểm tới đoạn thẳng
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

    # ------------------ Set Edge ------------------
    def set_edge(self, edge):
        statuses = ["normal", "traffic", "flood", "block"]
        status, ok = QInputDialog.getItem(
            self, f"Edge {edge['u']}-{edge['v']}", "Set status:", statuses, 0, False
        )
        if ok:
            edge["status"] = status
            self.update_edge_js(edge)
            set_edge_status(edge["edge_id"], status)

    # ------------------ Highlight Edge ------------------
    def highlight_edge(self, edge):
        u, v = edge["u"], edge["v"]
        lat1, lon1 = self.nodes[u]
        lat2, lon2 = self.nodes[v]
        js = f"""
        (function(){{
            let keys = Object.keys(window).filter(k=>k.startsWith("map_"));
            if(keys.length>0){{
                let mapObj = window[keys[0]];
                mapObj.eachLayer(function(layer){{
                    if(layer instanceof L.Polyline){{
                        let latlngs = layer.getLatLngs();
                        if(latlngs.length==2 &&
                           latlngs[0].lat=={lat1} && latlngs[0].lng=={lon1} &&
                           latlngs[1].lat=={lat2} && latlngs[1].lng=={lon2}){{
                               layer.setStyle({{color:"yellow", weight:5}});
                        }}
                    }}
                }});
            }}
        }})();
        """
        self.web.page().runJavaScript(js)

    # ------------------ Update Edge Color ------------------
    def update_edge_js(self, edge):
        u, v, status = edge["u"], edge["v"], edge["status"]
        lat1, lon1 = self.nodes[u]
        lat2, lon2 = self.nodes[v]
        color = STATUS_COLOR.get(status, "gray")
        js = f"""
        (function(){{
            let keys = Object.keys(window).filter(k=>k.startsWith("map_"));
            if(keys.length>0){{
                let mapObj = window[keys[0]];
                mapObj.eachLayer(function(layer){{
                    if(layer instanceof L.Polyline){{
                        let latlngs = layer.getLatLngs();
                        if(latlngs.length==2 &&
                           latlngs[0].lat=={lat1} && latlngs[0].lng=={lon1} &&
                           latlngs[1].lat=={lat2} && latlngs[1].lng=={lon2}){{
                               layer.setStyle({{color:"{color}", weight:3}});
                        }}
                    }}
                }});
            }}
        }})();
        """
        self.web.page().runJavaScript(js)


def main():
    app = QApplication(sys.argv)
    gui = AdminGUI()
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
