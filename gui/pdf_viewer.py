"""
Visor de PDF profesional con zoom, pan y scroll continuo.
"""
import fitz
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtGui import QPixmap, QImage, QPainter, QWheelEvent, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QTimer

from config import BASE_DPI, MIN_ZOOM, MAX_ZOOM, ZOOM_STEP, PAGE_GAP


class PDFViewerWidget(QGraphicsView):
    """
    Widget visor de PDF con:
    - Zoom con Ctrl+Scroll
    - Pan con clic + arrastrar
    - Scroll continuo de todas las páginas
    - Navegación por número de página
    - Ajustar a ancho / a página completa
    - Renderizado de alta calidad
    """
    page_changed = pyqtSignal(int, int)  # (página_actual, total_páginas)
    zoom_changed = pyqtSignal(int)       # porcentaje de zoom

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Configuración visual
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(QColor(60, 60, 60))

        # Estado interno
        self.doc = None
        self.current_page = 0
        self.zoom_level = 1.0
        self._pixmap_items: list[QGraphicsPixmapItem] = []
        self._page_positions: list[float] = []
        self._rendering = False

    def load_pdf(self, path: str):
        """Carga un PDF y renderiza todas las páginas."""
        self.close_doc()
        self.doc = fitz.open(path)
        self.current_page = 0
        self.zoom_level = 1.0
        self.resetTransform()
        self._render_all_pages()

    def _render_all_pages(self):
        """Renderiza todas las páginas en la escena."""
        if not self.doc or self._rendering:
            return

        self._rendering = True
        self._scene.clear()
        self._pixmap_items = []
        self._page_positions = []

        y_offset = 0.0
        dpi = BASE_DPI * self.zoom_level
        matrix = fitz.Matrix(dpi / 72, dpi / 72)

        for page_idx in range(len(self.doc)):
            page = self.doc[page_idx]
            pix = page.get_pixmap(matrix=matrix)

            # Convertir a QPixmap
            img = QImage(
                pix.samples, pix.width, pix.height,
                pix.stride, QImage.Format.Format_RGB888,
            )
            pixmap = QPixmap.fromImage(img)

            item = QGraphicsPixmapItem(pixmap)
            item.setPos(0, y_offset)
            self._scene.addItem(item)
            self._pixmap_items.append(item)
            self._page_positions.append(y_offset)

            y_offset += pixmap.height() + PAGE_GAP

        self._scene.setSceneRect(self._scene.itemsBoundingRect())
        self._rendering = False

        if self.doc:
            self.page_changed.emit(1, len(self.doc))
            self.zoom_changed.emit(self.get_zoom_percentage())

    # ---- Controles de Zoom ----

    def zoom_in(self):
        self.zoom_level = min(self.zoom_level * ZOOM_STEP, MAX_ZOOM)
        self._apply_zoom()

    def zoom_out(self):
        self.zoom_level = max(self.zoom_level / ZOOM_STEP, MIN_ZOOM)
        self._apply_zoom()

    def zoom_reset(self):
        self.zoom_level = 1.0
        self._apply_zoom()

    def zoom_fit_width(self):
        if not self.doc:
            return
        page = self.doc[self.current_page]
        page_width = page.rect.width * (BASE_DPI / 72)
        viewport_width = self.viewport().width() - 40
        if page_width > 0:
            self.zoom_level = viewport_width / page_width
            self._apply_zoom()

    def zoom_fit_page(self):
        if not self.doc:
            return
        page = self.doc[self.current_page]
        page_width = page.rect.width * (BASE_DPI / 72)
        page_height = page.rect.height * (BASE_DPI / 72)
        vw = self.viewport().width() - 40
        vh = self.viewport().height() - 40
        if page_width > 0 and page_height > 0:
            self.zoom_level = min(vw / page_width, vh / page_height)
            self._apply_zoom()

    def _apply_zoom(self):
        """Re-renderiza con el nuevo zoom, preservando posición de scroll."""
        scrollbar = self.verticalScrollBar()
        max_val = scrollbar.maximum()
        scroll_ratio = scrollbar.value() / max_val if max_val > 0 else 0

        self._render_all_pages()

        # Restaurar posición relativa
        QTimer.singleShot(50, lambda: scrollbar.setValue(
            int(scroll_ratio * scrollbar.maximum())
        ))

        self.zoom_changed.emit(self.get_zoom_percentage())

    # ---- Navegación ----

    def go_to_page(self, page_num: int):
        """Navega a una página específica (1-indexed)."""
        if not self.doc or not self._page_positions:
            return
        idx = max(0, min(page_num - 1, len(self.doc) - 1))
        self.current_page = idx

        if idx < len(self._page_positions):
            self.centerOn(QPointF(0, self._page_positions[idx]))
            self.page_changed.emit(idx + 1, len(self.doc))

    def get_zoom_percentage(self) -> int:
        return int(self.zoom_level * 100)

    # ---- Eventos ----

    def wheelEvent(self, event: QWheelEvent):
        """Ctrl+Scroll = zoom, Scroll normal = desplazamiento."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
            self._update_current_page()

    def _update_current_page(self):
        """Detecta la página visible actual por posición del scroll."""
        if not self._page_positions:
            return
        center_y = self.mapToScene(self.viewport().rect().center()).y()

        for i, pos in enumerate(self._page_positions):
            next_pos = (
                self._page_positions[i + 1]
                if i + 1 < len(self._page_positions)
                else float('inf')
            )
            if pos <= center_y < next_pos:
                if self.current_page != i:
                    self.current_page = i
                    self.page_changed.emit(i + 1, len(self.doc))
                return

    # ---- Limpieza ----

    def close_doc(self):
        if self.doc:
            self.doc.close()
            self.doc = None
        self._scene.clear()
        self._pixmap_items = []
        self._page_positions = []