from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
import sys

class TestView(QGraphicsView):
    def mousePressEvent(self, event):
        print("Clicked:", event.pos())
        super().mousePressEvent(event)

app = QApplication(sys.argv)
scene = QGraphicsScene()
view = TestView()
view.setScene(scene)
view.show()

sys.exit(app.exec_())
