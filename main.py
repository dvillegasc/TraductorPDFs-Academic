"""
PDF Academic Translator — Punto de entrada
===========================================
Ejecutar:
    python main.py
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # Estilo global
    app.setStyleSheet("""
        QMainWindow {
            background: #fafafa;
        }
        QTabWidget::pane {
            border: none;
        }
        QTabBar::tab {
            padding: 10px 24px;
            font-size: 13px;
            border: none;
            background: #e8e8e8;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }
        QTabBar::tab:selected {
            background: white;
            font-weight: bold;
            border-bottom: 3px solid #2196F3;
        }
        QTabBar::tab:hover {
            background: #d0d0d0;
        }
        QStatusBar {
            background: #f0f0f0;
            border-top: 1px solid #ddd;
            font-size: 12px;
        }
        QProgressBar {
            border: 1px solid #ccc;
            border-radius: 4px;
            text-align: center;
            background: #f0f0f0;
        }
        QProgressBar::chunk {
            background: #4CAF50;
            border-radius: 3px;
        }
        QSpinBox, QComboBox {
            padding: 4px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        QCheckBox {
            spacing: 6px;
            font-size: 12px;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()