"""
Barra de herramientas de la aplicación.
Contiene controles de archivo, traducción, zoom, navegación e idioma.
"""
from PyQt6.QtWidgets import (
    QToolBar, QPushButton, QLabel, QSpinBox, QComboBox,
    QProgressBar, QWidget, QHBoxLayout,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont

from core.languages import LanguageManager


class AppToolBar(QToolBar):
    """Barra de herramientas principal."""

    # Señales
    open_clicked = pyqtSignal()
    translate_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    zoom_in_clicked = pyqtSignal()
    zoom_out_clicked = pyqtSignal()
    fit_width_clicked = pyqtSignal()
    fit_page_clicked = pyqtSignal()
    page_changed = pyqtSignal(int)
    source_lang_changed = pyqtSignal(str)
    target_lang_changed = pyqtSignal(str)

    BUTTON_STYLE = """
        QPushButton {{
            padding: 7px 15px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            background: {bg};
            color: {fg};
            border: none;
        }}
        QPushButton:hover {{
            background: {hover};
        }}
        QPushButton:disabled {{
            background: #cccccc;
            color: #888888;
        }}
    """

    def __init__(self, parent=None):
        super().__init__("Herramientas", parent)
        self.setMovable(False)
        self.setIconSize(QSize(20, 20))
        self.setStyleSheet("""
            QToolBar {
                spacing: 5px; padding: 4px;
                background: #f5f5f5; border-bottom: 1px solid #ddd;
            }
        """)

        self._build_file_section()
        self.addSeparator()
        self._build_language_section()
        self.addSeparator()
        self._build_translate_section()
        self.addSeparator()
        self._build_zoom_section()
        self.addSeparator()
        self._build_page_section()
        self.addSeparator()
        self._build_save_section()

    def _make_button(self, text, bg, fg="white", hover=None) -> QPushButton:
        btn = QPushButton(text)
        if hover is None:
            hover = bg
        btn.setStyleSheet(self.BUTTON_STYLE.format(bg=bg, fg=fg, hover=hover))
        return btn

    # ---- Secciones ----

    def _build_file_section(self):
        self.btn_open = self._make_button("📂 Abrir PDF", "#2196F3")
        self.btn_open.clicked.connect(self.open_clicked.emit)
        self.addWidget(self.btn_open)

    def _build_language_section(self):
        # Idioma origen
        lbl_from = QLabel(" De: ")
        self.addWidget(lbl_from)

        self.combo_source = QComboBox()
        self.combo_source.setFixedWidth(200)
        for code, name in LanguageManager.get_source_languages():
            self.combo_source.addItem(name, code)
        self.combo_source.setCurrentIndex(0)  # English por defecto
        self.combo_source.currentIndexChanged.connect(
            lambda: self.source_lang_changed.emit(
                self.combo_source.currentData()
            )
        )
        self.addWidget(self.combo_source)

        lbl_arrow = QLabel(" → ")
        lbl_arrow.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.addWidget(lbl_arrow)

        # Idioma destino
        lbl_to = QLabel(" A: ")
        self.addWidget(lbl_to)

        self.combo_target = QComboBox()
        self.combo_target.setFixedWidth(200)
        for code, name in LanguageManager.get_target_languages():
            self.combo_target.addItem(name, code)
        self.combo_target.setCurrentIndex(0)  # Español por defecto
        self.combo_target.currentIndexChanged.connect(
            lambda: self.target_lang_changed.emit(
                self.combo_target.currentData()
            )
        )
        self.addWidget(self.combo_target)

    def _build_translate_section(self):
        self.btn_translate = self._make_button("🌐 Traducir", "#4CAF50")
        self.btn_translate.clicked.connect(self.translate_clicked.emit)
        self.btn_translate.setEnabled(False)
        self.addWidget(self.btn_translate)

        self.btn_cancel = self._make_button("⛔ Cancelar", "#f44336")
        self.btn_cancel.clicked.connect(self.cancel_clicked.emit)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.hide()
        self.addWidget(self.btn_cancel)

    def _build_zoom_section(self):
        lbl = QLabel(" Zoom: ")
        self.addWidget(lbl)

        self.btn_zoom_out = QPushButton("➖")
        self.btn_zoom_out.setFixedWidth(36)
        self.btn_zoom_out.clicked.connect(self.zoom_out_clicked.emit)
        self.addWidget(self.btn_zoom_out)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.addWidget(self.zoom_label)

        self.btn_zoom_in = QPushButton("➕")
        self.btn_zoom_in.setFixedWidth(36)
        self.btn_zoom_in.clicked.connect(self.zoom_in_clicked.emit)
        self.addWidget(self.btn_zoom_in)

        self.btn_fit_width = QPushButton("↔ Ancho")
        self.btn_fit_width.clicked.connect(self.fit_width_clicked.emit)
        self.addWidget(self.btn_fit_width)

        self.btn_fit_page = QPushButton("📄 Página")
        self.btn_fit_page.clicked.connect(self.fit_page_clicked.emit)
        self.addWidget(self.btn_fit_page)

    def _build_page_section(self):
        lbl = QLabel(" Pág: ")
        self.addWidget(lbl)

        self.page_spinner = QSpinBox()
        self.page_spinner.setMinimum(1)
        self.page_spinner.setMaximum(1)
        self.page_spinner.setFixedWidth(60)
        self.page_spinner.valueChanged.connect(self.page_changed.emit)
        self.addWidget(self.page_spinner)

        self.page_total_label = QLabel(" / 1")
        self.addWidget(self.page_total_label)

    def _build_save_section(self):
        self.btn_save = self._make_button("💾 Guardar", "#FF9800")
        self.btn_save.clicked.connect(self.save_clicked.emit)
        self.btn_save.setEnabled(False)
        self.addWidget(self.btn_save)

    # ---- Métodos públicos ----

    def update_zoom_label(self, percentage: int):
        self.zoom_label.setText(f"{percentage}%")

    def update_page_info(self, current: int, total: int):
        self.page_spinner.blockSignals(True)
        self.page_spinner.setMaximum(total)
        self.page_spinner.setValue(current)
        self.page_spinner.blockSignals(False)
        self.page_total_label.setText(f" / {total}")

    def set_translating(self, is_translating: bool):
        """Cambia el estado visual durante la traducción."""
        self.btn_open.setEnabled(not is_translating)
        self.btn_translate.setEnabled(not is_translating)
        self.btn_save.setEnabled(not is_translating and self.btn_save.isEnabled())
        self.combo_source.setEnabled(not is_translating)
        self.combo_target.setEnabled(not is_translating)

        self.btn_cancel.setVisible(is_translating)
        self.btn_cancel.setEnabled(is_translating)

    def get_source_lang(self) -> str:
        return self.combo_source.currentData() or "en"

    def get_target_lang(self) -> str:
        return self.combo_target.currentData() or "es"