import sys
import os
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Path to the root of the project
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    window = MainWindow(base_dir)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
