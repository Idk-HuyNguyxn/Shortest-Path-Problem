import sys
import os
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_DISABLE_FONT_HBASE"] = "1"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QT_QPA_PLATFORM"] = "windows:fontengine=freetype"

import tempfile
import folium
import json
import math

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))   # src/main
SRC_ROOT = os.path.dirname(CURRENT_DIR)                    # src
sys.path.insert(0, SRC_ROOT)

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QMessageBox, QComboBox, QPushButton, QLabel, QHBoxLayout
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QObject, pyqtSlot, QUrl
from PyQt5.QtWebChannel import QWebChannel

from utils.map_handler import load_graph_from_db
from utils.map_handler import get_map_center
from algorithms.astar import astar
from algorithms.dijkstra import dijkstra

MAP_HTML = os.path.join(tempfile.gettempdir(), "map_gui_click.html")


# ----------------------
# Helper: tìm node gần nhất
# ----------------------
def find_nearest_node(lat, lon, nodes):
    best_id = None
    best_dist = 1e18

    for nid, (nlat, nlon) in nodes.items():
        d = (lat - nlat)**2 + (lon - nlon)**2  # đủ nhanh, không cần Haversine
        if d < best_dist:
            best_dist = d
            best_id = nid

    return best_id


def create_map_with_js(center):
    """
    Tạo folium Map + thêm JS bắt sự kiện click + WebChannel
    """
    m = folium.Map(location=center, zoom_start=17)

    m.get_root().header.add_child(folium.Element("""
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    """))
    return m


def save_map(m):
    m.save(MAP_HTML)


def draw_path_on_map(m, nodes, path):
    if not path:
        return
    
    coords = [nodes[n] for n in path]

    folium.Marker(nodes[path[0]], tooltip="START", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(nodes[path[-1]], tooltip="GOAL", icon=folium.Icon(color="red")).add_to(m)

    folium.PolyLine(coords, color="blue", weight=6).add_to(m)


# -------------------------------
# Object nhận sự kiện từ JavaScript
# -------------------------------
class JsBridge(QObject):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui

    @pyqtSlot(float, float)
    def onMapClick(self, lat, lon):
        print("PY received click:", lat, lon)
        self.gui.map_clicked(lat, lon)


# -------------------------------
# GUI chính
# -------------------------------
class MapGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("A* + Dijkstra Map Selector")
        self.resize(1000, 700)

        # load DB
        self.graph, self.nodes = load_graph_from_db()

        self.start_node = None
        self.goal_node = None

        # layout
        layout = QVBoxLayout(self)

        # control bar
        bar = QHBoxLayout()
        self.alg = QComboBox()
        self.alg.addItems(["A*", "Dijkstra"])
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.reset_selection)
        bar.addWidget(QLabel("Algorithm:"))
        bar.addWidget(self.alg)
        bar.addWidget(self.clear_btn)
        bar.addStretch()
        layout.addLayout(bar)

        # Web view
        self.web = QWebEngineView()
        layout.addWidget(self.web)

        # Create map
        lat_avg, lon_avg = get_map_center()
        m = create_map_with_js((lat_avg, lon_avg))
        save_map(m)
        
        # Setup JS bridge
        self.channel = QWebChannel()
        self.js_bridge = JsBridge(self)
        self.channel.registerObject("pyHandler", self.js_bridge)
        self.web.page().setWebChannel(self.channel)

        # Load HTML
        self.web.load(QUrl.fromLocalFile(MAP_HTML))

        # Inject JS to connect click handler
        self.web.loadFinished.connect(self.inject_js)

    def inject_js(self):
        init_js = r"""
            (function() {
                function waitForTransport(cb) {
                    if (typeof qt !== 'undefined' && qt.webChannelTransport) return cb();
                    setTimeout(function(){ waitForTransport(cb); }, 50);
                }

                waitForTransport(function() {
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        window.pyHandler = channel.objects.pyHandler;

                        function attachClickToMap() {
                            // tìm biến map dạng map_xxx
                            let keys = Object.keys(window)
                                .filter(k => k.startsWith("map_"));

                            if (keys.length === 0) {
                                setTimeout(attachClickToMap, 50);
                                return;
                            }

                            let mapObj = window[keys[0]];
                            if (!mapObj._py_click_attached) {
                                mapObj._py_click_attached = true;

                                mapObj.on('click', function(e) {
                                    pyHandler.onMapClick(e.latlng.lat, e.latlng.lng);
                                });
                            }
                        }

                        attachClickToMap();
                    });
                });
            })();
        """
        self.web.page().runJavaScript(init_js)

    # ---------------------------
    # Khi click lên map
    # ---------------------------
    def map_clicked(self, lat, lon):
        if self.start_node is None:
            self.start_node = find_nearest_node(lat, lon, self.nodes)
            QMessageBox.information(self, "Start Selected",
                                    f"Start node = {self.start_node}")
            return

        if self.goal_node is None:
            self.goal_node = find_nearest_node(lat, lon, self.nodes)
            QMessageBox.information(self, "Goal Selected",
                                    f"Goal node = {self.goal_node}")

            # chạy thuật toán
            self.run_algorithm()
            return

    # ---------------------------
    # Chạy thuật toán
    # ---------------------------
    def run_algorithm(self):
        algo = self.alg.currentText()

        if algo == "A*":
            path = astar(self.graph, self.nodes, self.start_node, self.goal_node)
            if path is None:
                QMessageBox.warning(self, "Error", "No path found by A*")
                return
        else:
            path, dist = dijkstra(self.graph, self.nodes, self.start_node, self.goal_node)
            if path is None:
                QMessageBox.warning(self, "Error", "No path found by Dijkstra")
                return

        # tạo map mới
        m = create_map_with_js(self.nodes[self.start_node])
        draw_path_on_map(m, self.nodes, path)
        save_map(m)

        self.web.reload()

    # ---------------------------
    # Reset chọn start/goal
    # ---------------------------
    def reset_selection(self):
        self.start_node = None
        self.goal_node = None

        lat_avg, lon_avg = get_map_center()  # dùng center trung bình
        m = create_map_with_js((lat_avg, lon_avg))
        save_map(m)
        self.web.reload()



# ---------------------------
# Hàm main_Gui
# ---------------------------
def main_Gui():
    app = QApplication(sys.argv)
    gui = MapGUI()
    gui.show()
    return app.exec_()

if __name__ == "__main__":
    main_Gui()