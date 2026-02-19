"""
Detector de tablas en PDFs.
Identifica las coordenadas de tablas para crear zonas de exclusión.

Estrategia:
- Usar las líneas vectoriales (drawings) del PDF para encontrar
  los rectángulos que forman la cuadrícula de una tabla.
- Si PyMuPDF no encuentra líneas (tabla sin bordes), usar heurística
  basada en alineación vertical/horizontal de bloques de texto cortos.
"""
import fitz
from dataclasses import dataclass, field


@dataclass
class TableRegion:
    """Región rectangular que contiene una tabla."""
    rect: fitz.Rect
    page_index: int
    confidence: float = 1.0  # 0.0-1.0, qué tan seguro estamos
    has_borders: bool = True  # Si la tabla tiene líneas visibles

    def contains_point(self, x: float, y: float) -> bool:
        """Verifica si un punto está dentro de la región de la tabla."""
        return (self.rect.x0 <= x <= self.rect.x1 and
                self.rect.y0 <= y <= self.rect.y1)

    def intersects_rect(self, other: fitz.Rect) -> bool:
        """Verifica si otro rectángulo se solapa con esta tabla."""
        return self.rect.intersects(other)

    def contains_rect(self, other: fitz.Rect) -> bool:
        """Verifica si otro rectángulo está COMPLETAMENTE dentro de la tabla."""
        return (self.rect.x0 <= other.x0 and
                self.rect.y0 <= other.y0 and
                self.rect.x1 >= other.x1 and
                self.rect.y1 >= other.y1)

    def overlaps_significantly(self, other: fitz.Rect, threshold: float = 0.5) -> bool:
        """
        Verifica si otro rectángulo se solapa significativamente.
        threshold=0.5 significa que al menos 50% del bloque está dentro de la tabla.
        """
        if not self.rect.intersects(other):
            return False

        # Calcular área de intersección
        ix0 = max(self.rect.x0, other.x0)
        iy0 = max(self.rect.y0, other.y0)
        ix1 = min(self.rect.x1, other.x1)
        iy1 = min(self.rect.y1, other.y1)

        if ix0 >= ix1 or iy0 >= iy1:
            return False

        intersection_area = (ix1 - ix0) * (iy1 - iy0)
        block_area = max((other.x1 - other.x0) * (other.y1 - other.y0), 1)

        return (intersection_area / block_area) >= threshold


class TableDetector:
    """
    Detecta tablas en páginas de PDF.
    
    Métodos de detección (en orden de confiabilidad):
    1. Detección por líneas vectoriales (tablas con bordes)
    2. Detección por find_tables() de PyMuPDF (si disponible)
    3. Heurística de alineación (tablas sin bordes)
    """

    # Parámetros de detección
    MIN_TABLE_LINES = 3          # Mínimo de líneas para considerar tabla
    MIN_TABLE_WIDTH = 100        # Ancho mínimo en pts
    MIN_TABLE_HEIGHT = 40        # Alto mínimo en pts
    LINE_TOLERANCE = 3           # Tolerancia para alinear líneas (pts)
    PADDING = 5                  # Padding extra alrededor de la tabla (pts)

    @classmethod
    def detect_tables_in_page(cls, page: fitz.Page) -> list[TableRegion]:
        """
        Detecta todas las tablas en una página.
        Combina múltiples métodos para máxima cobertura.
        """
        tables = []

        # Método 1: Detección por find_tables() de PyMuPDF
        tables_from_api = cls._detect_with_find_tables(page)
        tables.extend(tables_from_api)

        # Método 2: Detección por líneas vectoriales
        if not tables_from_api:
            tables_from_lines = cls._detect_from_lines(page)
            tables.extend(tables_from_lines)

        # Método 3: Heurística de alineación (tablas sin bordes)
        if not tables:
            tables_from_heuristic = cls._detect_from_alignment(page)
            tables.extend(tables_from_heuristic)

        # Eliminar duplicados (tablas que se solapan)
        tables = cls._merge_overlapping(tables)

        return tables

    @classmethod
    def detect_all_tables(cls, doc: fitz.Document) -> dict[int, list[TableRegion]]:
        """
        Detecta tablas en TODAS las páginas del documento.
        
        Returns:
            Diccionario {page_index: [TableRegion, ...]}
        """
        all_tables = {}
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_tables = cls.detect_tables_in_page(page)
            if page_tables:
                all_tables[page_idx] = page_tables
        return all_tables

    @classmethod
    def _detect_with_find_tables(cls, page: fitz.Page) -> list[TableRegion]:
        """Usa la función find_tables() de PyMuPDF (v1.23.0+)."""
        tables = []
        try:
            found = page.find_tables()
            if found and found.tables:
                for table in found.tables:
                    rect = fitz.Rect(table.bbox)
                    # Agregar padding
                    rect = fitz.Rect(
                        rect.x0 - cls.PADDING,
                        rect.y0 - cls.PADDING,
                        rect.x1 + cls.PADDING,
                        rect.y1 + cls.PADDING,
                    )
                    tables.append(TableRegion(
                        rect=rect,
                        page_index=page.number,
                        confidence=0.95,
                        has_borders=True,
                    ))
        except (AttributeError, Exception):
            # find_tables() no disponible en esta versión de PyMuPDF
            pass
        return tables

    @classmethod
    def _detect_from_lines(cls, page: fitz.Page) -> list[TableRegion]:
        """
        Detecta tablas analizando las líneas vectoriales del PDF.
        Las tablas con bordes tienen muchas líneas horizontales y verticales
        concentradas en la misma área.
        """
        tables = []

        try:
            drawings = page.get_drawings()
        except Exception:
            return tables

        if not drawings:
            return tables

        # Separar líneas horizontales y verticales
        h_lines = []  # Líneas horizontales
        v_lines = []  # Líneas verticales

        for drawing in drawings:
            for item in drawing.get("items", []):
                if item[0] == "l":  # Es una línea
                    p1, p2 = item[1], item[2]
                    dx = abs(p2.x - p1.x)
                    dy = abs(p2.y - p1.y)

                    if dy < cls.LINE_TOLERANCE and dx > 20:
                        h_lines.append((
                            min(p1.x, p2.x), p1.y,
                            max(p1.x, p2.x), p2.y
                        ))
                    elif dx < cls.LINE_TOLERANCE and dy > 10:
                        v_lines.append((
                            p1.x, min(p1.y, p2.y),
                            p2.x, max(p1.y, p2.y)
                        ))

                elif item[0] == "re":  # Es un rectángulo
                    rect = item[1]
                    if isinstance(rect, fitz.Rect):
                        if rect.width > cls.MIN_TABLE_WIDTH and rect.height > cls.MIN_TABLE_HEIGHT:
                            tables.append(TableRegion(
                                rect=fitz.Rect(
                                    rect.x0 - cls.PADDING,
                                    rect.y0 - cls.PADDING,
                                    rect.x1 + cls.PADDING,
                                    rect.y1 + cls.PADDING,
                                ),
                                page_index=page.number,
                                confidence=0.85,
                                has_borders=True,
                            ))

        # Si hay suficientes líneas H y V en la misma zona → tabla
        if len(h_lines) >= cls.MIN_TABLE_LINES and len(v_lines) >= 2:
            # Encontrar el bounding box que engloba todas las líneas
            all_coords = h_lines + v_lines
            x0 = min(c[0] for c in all_coords)
            y0 = min(c[1] for c in all_coords)
            x1 = max(c[2] for c in all_coords)
            y1 = max(c[3] for c in all_coords)

            rect = fitz.Rect(
                x0 - cls.PADDING, y0 - cls.PADDING,
                x1 + cls.PADDING, y1 + cls.PADDING,
            )

            if rect.width >= cls.MIN_TABLE_WIDTH and rect.height >= cls.MIN_TABLE_HEIGHT:
                tables.append(TableRegion(
                    rect=rect,
                    page_index=page.number,
                    confidence=0.80,
                    has_borders=True,
                ))

        return tables

    @classmethod
    def _detect_from_alignment(cls, page: fitz.Page) -> list[TableRegion]:
        """
        Heurística para tablas SIN bordes visibles.
        Detecta grupos de bloques de texto cortos alineados en columnas.
        """
        tables = []
        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if b[6] == 0]  # Solo texto

        if len(text_blocks) < 6:
            return tables

        # Agrupar bloques por posición Y similar (misma fila)
        rows = {}
        for block in text_blocks:
            y_key = round(block[1] / 8) * 8  # Redondear Y a múltiplos de 8
            if y_key not in rows:
                rows[y_key] = []
            rows[y_key].append(block)

        # Buscar secuencias de filas con el mismo número de "columnas"
        row_keys = sorted(rows.keys())
        consecutive_table_rows = []
        current_group = []

        for key in row_keys:
            row_blocks = rows[key]
            n_cols = len(row_blocks)

            if n_cols >= 3:  # Al menos 3 columnas
                current_group.append((key, row_blocks))
            else:
                if len(current_group) >= 3:  # Al menos 3 filas consecutivas
                    consecutive_table_rows.append(current_group)
                current_group = []

        if len(current_group) >= 3:
            consecutive_table_rows.append(current_group)

        # Crear TableRegion para cada grupo
        for group in consecutive_table_rows:
            all_blocks = []
            for _, row_blocks in group:
                all_blocks.extend(row_blocks)

            x0 = min(b[0] for b in all_blocks)
            y0 = min(b[1] for b in all_blocks)
            x1 = max(b[2] for b in all_blocks)
            y1 = max(b[3] for b in all_blocks)

            rect = fitz.Rect(
                x0 - cls.PADDING, y0 - cls.PADDING,
                x1 + cls.PADDING, y1 + cls.PADDING,
            )

            if rect.width >= cls.MIN_TABLE_WIDTH and rect.height >= cls.MIN_TABLE_HEIGHT:
                tables.append(TableRegion(
                    rect=rect,
                    page_index=page.number,
                    confidence=0.60,
                    has_borders=False,
                ))

        return tables

    @classmethod
    def _merge_overlapping(cls, tables: list[TableRegion]) -> list[TableRegion]:
        """Fusiona tablas que se solapan para evitar duplicados."""
        if len(tables) <= 1:
            return tables

        merged = []
        used = set()

        for i, t1 in enumerate(tables):
            if i in used:
                continue

            current_rect = t1.rect
            current_conf = t1.confidence

            for j, t2 in enumerate(tables):
                if j <= i or j in used:
                    continue

                if current_rect.intersects(t2.rect):
                    # Fusionar: tomar el bounding box más grande
                    current_rect = fitz.Rect(
                        min(current_rect.x0, t2.rect.x0),
                        min(current_rect.y0, t2.rect.y0),
                        max(current_rect.x1, t2.rect.x1),
                        max(current_rect.y1, t2.rect.y1),
                    )
                    current_conf = max(current_conf, t2.confidence)
                    used.add(j)

            merged.append(TableRegion(
                rect=current_rect,
                page_index=t1.page_index,
                confidence=current_conf,
                has_borders=t1.has_borders,
            ))
            used.add(i)

        return merged