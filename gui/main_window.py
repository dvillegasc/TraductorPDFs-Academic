"""
Ventana principal de la aplicación.
Gestiona las 3 pestañas, la toolbar, el statusbar y la lógica de la UI.
"""
import os
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFileDialog, QMessageBox, QStatusBar, QProgressBar,
    QSplitter, QCheckBox,
)
from PyQt6.QtGui import QAction, QKeySequence, QFont
from PyQt6.QtCore import Qt

from config import (
    APP_NAME, APP_VERSION, WINDOW_TITLE,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT,
)
from gui.pdf_viewer import PDFViewerWidget
from gui.toolbar import AppToolBar
from gui.translation_worker import TranslationWorker


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        # Estado
        self.original_path: str | None = None
        self.translated_path: str | None = None
        self.worker: TranslationWorker | None = None

        self._setup_ui()
        self._setup_toolbar()
        self._setup_statusbar()
        self._setup_shortcuts()

    # ================================================================
    #  SETUP DE LA INTERFAZ
    # ================================================================

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)
        tab_font = QFont()
        tab_font.setPointSize(11)
        self.tabs.setFont(tab_font)

        # --- Tab 1: Original ---
        self.viewer_original = PDFViewerWidget()
        tab1 = QWidget()
        lay1 = QVBoxLayout(tab1)
        lay1.setContentsMargins(0, 0, 0, 0)
        lay1.addWidget(self.viewer_original)
        self.tabs.addTab(tab1, "📖 Original")

        # --- Tab 2: Traducido ---
        self.viewer_translated = PDFViewerWidget()
        tab2 = QWidget()
        lay2 = QVBoxLayout(tab2)
        lay2.setContentsMargins(0, 0, 0, 0)

        self.translated_placeholder = QLabel(
            "⏳ Carga un PDF y presiona 'Traducir' para ver la versión traducida."
        )
        self.translated_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.translated_placeholder.setFont(QFont("Arial", 14))
        self.translated_placeholder.setStyleSheet("color: #888; padding: 40px;")

        lay2.addWidget(self.translated_placeholder)
        lay2.addWidget(self.viewer_translated)
        self.viewer_translated.hide()
        self.tabs.addTab(tab2, "📝 Traducido")

        # --- Tab 3: Comparar ---
        self.viewer_cmp_left = PDFViewerWidget()
        self.viewer_cmp_right = PDFViewerWidget()

        tab3 = QWidget()
        lay3 = QVBoxLayout(tab3)
        lay3.setContentsMargins(0, 0, 0, 0)

        # Encabezados
        header_layout = QHBoxLayout()
        lbl_left = QLabel("  🔵 ORIGINAL")
        lbl_left.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lbl_left.setStyleSheet(
            "color: #2196F3; padding: 5px; background: #f0f0f0;"
        )
        lbl_right = QLabel("  🟢 TRADUCIDO")
        lbl_right.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lbl_right.setStyleSheet(
            "color: #4CAF50; padding: 5px; background: #f0f0f0;"
        )
        header_layout.addWidget(lbl_left)
        header_layout.addWidget(lbl_right)
        lay3.addLayout(header_layout)

        self.compare_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.compare_splitter.addWidget(self.viewer_cmp_left)
        self.compare_splitter.addWidget(self.viewer_cmp_right)
        self.compare_splitter.setSizes([600, 600])
        self.compare_splitter.hide()

        self.compare_placeholder = QLabel(
            "⏳ Traduce un PDF para comparar ambas versiones lado a lado."
        )
        self.compare_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.compare_placeholder.setFont(QFont("Arial", 14))
        self.compare_placeholder.setStyleSheet("color: #888; padding: 40px;")

        lay3.addWidget(self.compare_splitter)
        lay3.addWidget(self.compare_placeholder)
        self.tabs.addTab(tab3, "🔄 Comparar")

        layout.addWidget(self.tabs)

        # Sincronizar scroll en comparación
        self._sync_scrolls(self.viewer_cmp_left, self.viewer_cmp_right)

    def _sync_scrolls(self, v1: PDFViewerWidget, v2: PDFViewerWidget):
        """Sincroniza el scroll vertical entre dos visores."""
        def sync_1_to_2(val):
            sb1, sb2 = v1.verticalScrollBar(), v2.verticalScrollBar()
            if sb1.maximum() > 0:
                sb2.setValue(int((val / sb1.maximum()) * sb2.maximum()))

        def sync_2_to_1(val):
            sb1, sb2 = v1.verticalScrollBar(), v2.verticalScrollBar()
            if sb2.maximum() > 0:
                sb1.setValue(int((val / sb2.maximum()) * sb1.maximum()))

        v1.verticalScrollBar().valueChanged.connect(sync_1_to_2)
        v2.verticalScrollBar().valueChanged.connect(sync_2_to_1)

    def _setup_toolbar(self):
        self.toolbar = AppToolBar(self)
        self.addToolBar(self.toolbar)

        # Conectar señales de la toolbar
        self.toolbar.open_clicked.connect(self.open_pdf)
        self.toolbar.translate_clicked.connect(self.start_translation)
        self.toolbar.cancel_clicked.connect(self.cancel_translation)
        self.toolbar.save_clicked.connect(self.save_translation)
        self.toolbar.zoom_in_clicked.connect(self._zoom_in)
        self.toolbar.zoom_out_clicked.connect(self._zoom_out)
        self.toolbar.fit_width_clicked.connect(self._fit_width)
        self.toolbar.fit_page_clicked.connect(self._fit_page)
        self.toolbar.page_changed.connect(self._go_to_page)

        # Conectar señales de los visores
        all_viewers = [
            self.viewer_original, self.viewer_translated,
            self.viewer_cmp_left, self.viewer_cmp_right,
        ]
        for viewer in all_viewers:
            viewer.page_changed.connect(self.toolbar.update_page_info)
            viewer.zoom_changed.connect(self.toolbar.update_zoom_label)

    def _setup_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Checkbox OCR
        self.chk_ocr = QCheckBox("🔍 Aplicar OCR (PDFs escaneados)")
        self.chk_ocr.setToolTip(
            "Activa esta opción si el PDF es una imagen escaneada.\n"
            "Requiere Tesseract instalado."
        )
        self.statusbar.addWidget(self.chk_ocr)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(300)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        self.statusbar.addPermanentWidget(self.progress_bar)

        # Label de estado
        self.status_label = QLabel(f"  {APP_NAME} v{APP_VERSION} — Listo")
        self.statusbar.addPermanentWidget(self.status_label)

    def _setup_shortcuts(self):
        shortcuts = {
            "Ctrl+O": self.open_pdf,
            "Ctrl+T": self.start_translation,
            "Ctrl+S": self.save_translation,
            "Ctrl++": self._zoom_in,
            "Ctrl+-": self._zoom_out,
            "Ctrl+0": self._zoom_reset,
        }
        for keys, slot in shortcuts.items():
            action = QAction(self)
            action.setShortcut(QKeySequence(keys))
            action.triggered.connect(slot)
            self.addAction(action)

    # ================================================================
    #  VISOR ACTIVO SEGÚN LA PESTAÑA
    # ================================================================

    def _get_active_viewer(self) -> PDFViewerWidget:
        idx = self.tabs.currentIndex()
        if idx == 0:
            return self.viewer_original
        elif idx == 1:
            return self.viewer_translated
        else:
            return self.viewer_cmp_left

    def _zoom_in(self):
        v = self._get_active_viewer()
        v.zoom_in()
        if self.tabs.currentIndex() == 2:
            self.viewer_cmp_right.zoom_level = v.zoom_level
            self.viewer_cmp_right._apply_zoom()

    def _zoom_out(self):
        v = self._get_active_viewer()
        v.zoom_out()
        if self.tabs.currentIndex() == 2:
            self.viewer_cmp_right.zoom_level = v.zoom_level
            self.viewer_cmp_right._apply_zoom()

    def _zoom_reset(self):
        v = self._get_active_viewer()
        v.zoom_reset()
        if self.tabs.currentIndex() == 2:
            self.viewer_cmp_right.zoom_reset()

    def _fit_width(self):
        self._get_active_viewer().zoom_fit_width()

    def _fit_page(self):
        self._get_active_viewer().zoom_fit_page()

    def _go_to_page(self, page_num: int):
        self._get_active_viewer().go_to_page(page_num)

    # ================================================================
    #  ACCIONES PRINCIPALES
    # ================================================================

    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir PDF", "",
            "Archivos PDF (*.pdf);;Todos (*)"
        )
        if not path:
            return

        self.original_path = path
        self.translated_path = None

        self.viewer_original.load_pdf(path)
        self.tabs.setCurrentIndex(0)

        # Resetear traducción
        self.viewer_translated.hide()
        self.translated_placeholder.show()
        self.translated_placeholder.setText(
            "⏳ Presiona 'Traducir' para generar la versión traducida."
        )
        self.compare_splitter.hide()
        self.compare_placeholder.show()

        self.toolbar.btn_translate.setEnabled(True)
        self.toolbar.btn_save.setEnabled(False)

        filename = Path(path).name
        self.status_label.setText(f"  Archivo: {filename}")
        self.setWindowTitle(f"📄 {APP_NAME} — {filename}")

    def start_translation(self):
        if not self.original_path:
            QMessageBox.warning(self, "Aviso", "Primero abre un archivo PDF.")
            return

        # Leer configuración de la toolbar
        source = self.toolbar.get_source_lang()
        target = self.toolbar.get_target_lang()
        apply_ocr = self.chk_ocr.isChecked()

        if source == target:
            QMessageBox.warning(
                self, "Aviso",
                "El idioma de origen y destino son iguales.\n"
                "Selecciona idiomas diferentes."
            )
            return

        # Preparar UI
        self.toolbar.set_translating(True)
        self.progress_bar.show()
        self.progress_bar.setValue(0)

        # Crear worker
        self.worker = TranslationWorker(
            input_path=self.original_path,
            source_lang=source,
            target_lang=target,
            apply_ocr=apply_ocr,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.status.connect(self._on_status)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.stats.connect(self._on_stats)
        self.worker.start()

    def cancel_translation(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
        self._reset_ui()
        self.status_label.setText("  Traducción cancelada.")

    def save_translation(self):
        if not self.translated_path:
            QMessageBox.warning(self, "Aviso", "No hay traducción para guardar.")
            return

        original_stem = Path(self.original_path).stem
        target_lang = self.toolbar.get_target_lang()
        suggested = f"{original_stem}_{target_lang}.pdf"

        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF Traducido", suggested,
            "Archivos PDF (*.pdf)"
        )
        if not path:
            return

        try:
            shutil.copy2(self.translated_path, path)
            self.status_label.setText(f"  ✅ Guardado: {path}")
            QMessageBox.information(
                self, "Guardado",
                f"PDF traducido guardado en:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")

    # ================================================================
    #  CALLBACKS DEL WORKER
    # ================================================================

    def _on_progress(self, value: int):
        self.progress_bar.setValue(value)

    def _on_status(self, msg: str):
        self.status_label.setText(f"  {msg}")

    def _on_stats(self, summary: str):
        """Muestra las estadísticas de traducción."""
        QMessageBox.information(self, "Estadísticas", summary)

    def _on_finished(self, output_path: str):
        self.translated_path = output_path

        # Mostrar PDF traducido
        self.translated_placeholder.hide()
        self.viewer_translated.show()
        self.viewer_translated.load_pdf(output_path)

        # Cargar en comparación
        self.compare_placeholder.hide()
        self.compare_splitter.show()
        self.viewer_cmp_left.load_pdf(self.original_path)
        self.viewer_cmp_right.load_pdf(output_path)

        # Restaurar UI
        self._reset_ui()
        self.toolbar.btn_save.setEnabled(True)
        self.status_label.setText("  ✅ ¡Traducción completada!")
        self.tabs.setCurrentIndex(1)

        QMessageBox.information(
            self, "Éxito",
            "¡Traducción finalizada!\n\n"
            "• Pestaña 'Traducido' → Ver resultado\n"
            "• Pestaña 'Comparar' → Ver lado a lado\n"
            "• Botón 'Guardar' → Exportar el PDF"
        )

    def _on_error(self, msg: str):
        self._reset_ui()
        self.status_label.setText(f"  ❌ Error")
        QMessageBox.critical(self, "Error de Traducción", msg)

    def _reset_ui(self):
        self.toolbar.set_translating(False)
        self.progress_bar.hide()

    # ================================================================
    #  LIMPIEZA
    # ================================================================

    def closeEvent(self, event):
        # Cancelar traducción en curso
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)

        # Cerrar documentos PDF
        for viewer in [
            self.viewer_original, self.viewer_translated,
            self.viewer_cmp_left, self.viewer_cmp_right,
        ]:
            viewer.close_doc()

        # Limpiar archivo temporal
        if self.translated_path and os.path.exists(self.translated_path):
            try:
                os.remove(self.translated_path)
            except OSError:
                pass

        event.accept()