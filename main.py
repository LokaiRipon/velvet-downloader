# main.py
import sys
from PyQt6.QtWidgets import QApplication
from app import VelvetDownApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VelvetDownApp()
    window.show()
    sys.exit(app.exec())