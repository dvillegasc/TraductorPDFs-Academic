"""
Motor de Layout v3 — Con soporte de fuentes Unicode.
"""
import fitz
from config import (
    HEADER_MARGIN_PTS, FOOTER_MARGIN_PTS,
    MAX_FONTSIZE, MIN_FONTSIZE,
    FONTSIZE_REDUCTION_STEPS, FONTSIZE_REDUCTION_FACTOR,
    MAX_RECT_EXPANSION_PTS,
)
from core.font_manager import FontManager


class LayoutEngine:
    """Posicionamiento inteligente con fuentes Unicode."""

    def __init__(self):
        self.overflow_count = 0
        self._table_regions = []
        self._formula_rects = []
        self.font_manager = FontManager()

    def set_table_regions(self, regions: list):
        self._table_regions = regions or []

    def add_formula_rect(self, rect: fitz.Rect):
        self._formula_rects.append(rect)

    def clear_page_state(self):
        self._table_regions = []
        self._formula_rects = []

    def register_fonts_for_page(self, page: fitz.Page):
        """Registra las fuentes Unicode en una página. Llamar una vez por página."""
        self.font_manager.register_all_variants(page)

    def is_header_or_footer(
        self, block_rect: fitz.Rect, page_rect: fitz.Rect
    ) -> bool:
        if block_rect.y0 < HEADER_MARGIN_PTS:
            return True
        if block_rect.y1 > (page_rect.height - FOOTER_MARGIN_PTS):
            return True
        return False

    def is_inside_table(self, block_rect: fitz.Rect) -> bool:
        for table in self._table_regions:
            if table.overlaps_significantly(block_rect, threshold=0.4):
                return True
        return False

    def would_overlap_formula(self, rect: fitz.Rect) -> bool:
        expanded = fitz.Rect(
            rect.x0 - 2, rect.y0 - 2,
            rect.x1 + 2, rect.y1 + 2,
        )
        for formula_rect in self._formula_rects:
            if expanded.intersects(formula_rect):
                return True
        return False

    def get_occupied_zones(self, page: fitz.Page) -> list[fitz.Rect]:
        zones = []
        for img in page.get_images(full=True):
            try:
                for r in page.get_image_rects(img[0]):
                    zones.append(r)
            except Exception:
                pass
        for block in page.get_text("blocks"):
            if block[6] == 0:
                zones.append(fitz.Rect(block[:4]))
        for table in self._table_regions:
            zones.append(table.rect)
        for fr in self._formula_rects:
            zones.append(fr)
        return zones

    def get_free_space_below(
        self, block_rect: fitz.Rect,
        occupied_zones: list[fitz.Rect],
        page_rect: fitz.Rect,
    ) -> float:
        y_limit = page_rect.height - FOOTER_MARGIN_PTS
        for zone in occupied_zones:
            if (zone.y0 > block_rect.y1 and
                zone.x0 < block_rect.x1 and
                zone.x1 > block_rect.x0):
                y_limit = min(y_limit, zone.y0)
        return max(y_limit - block_rect.y1, 0)

    def extract_block_format(self, page: fitz.Page, block_rect: fitz.Rect) -> dict:
        format_info = {
            "fontsize": 10,
            "color": (0, 0, 0),
            "is_bold": False,
            "is_italic": False,
            "align": 0,
        }
        try:
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                if not fitz.Rect(block["bbox"]).intersects(block_rect):
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if len(span["text"].strip()) > 2:
                            format_info["fontsize"] = span["size"]
                            format_info["is_bold"] = bool(span["flags"] & 16)
                            format_info["is_italic"] = bool(span["flags"] & 2)
                            c = span["color"]
                            format_info["color"] = (
                                (c >> 16 & 0xFF) / 255,
                                (c >> 8 & 0xFF) / 255,
                                (c & 0xFF) / 255,
                            )
                            return format_info
        except Exception:
            pass
        return format_info

    def insert_translated_text(
        self, page: fitz.Page, rect: fitz.Rect,
        text: str, format_info: dict,
        occupied_zones: list[fitz.Rect],
    ) -> bool:
        """Inserta texto con fuente Unicode y ajuste inteligente."""
        page_rect = page.rect
        fontsize = min(format_info["fontsize"], MAX_FONTSIZE)

        if self.would_overlap_formula(rect):
            return self._insert_without_background(
                page, rect, text, fontsize, format_info
            )

        # Obtener nombre de fuente Unicode según estilo
        fontname = self.font_manager.get_fontname(
            bold=format_info["is_bold"],
            italic=format_info["is_italic"],
        )
        color = format_info["color"]

        # --- Estrategia 1: Tamaño original, reducir progresivamente ---
        for step in range(FONTSIZE_REDUCTION_STEPS):
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

            result = page.insert_textbox(
                rect, text,
                fontsize=fontsize,
                fontname=fontname,
                color=color,
                align=format_info["align"],
            )

            if result >= 0:
                return True

            fontsize *= FONTSIZE_REDUCTION_FACTOR
            if fontsize < MIN_FONTSIZE:
                break

        # --- Estrategia 2: Expandir hacia abajo ---
        free_space = self.get_free_space_below(rect, occupied_zones, page_rect)

        if free_space > 5:
            expansion = min(free_space * 0.8, MAX_RECT_EXPANSION_PTS)
            expanded = fitz.Rect(
                rect.x0, rect.y0, rect.x1, rect.y1 + expansion
            )

            safe = True
            for table in self._table_regions:
                if table.intersects_rect(expanded):
                    safe = False
                    break
            for fr in self._formula_rects:
                if expanded.intersects(fr):
                    safe = False
                    break

            if safe:
                page.draw_rect(expanded, color=(1, 1, 1), fill=(1, 1, 1))
                result = page.insert_textbox(
                    expanded, text,
                    fontsize=max(fontsize, MIN_FONTSIZE + 0.5),
                    fontname=fontname,
                    color=color,
                    align=format_info["align"],
                )
                if result >= 0:
                    return True

        # --- Estrategia 3: Lo que quepa + overflow ---
        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
        page.insert_textbox(
            rect, text,
            fontsize=max(fontsize, MIN_FONTSIZE),
            fontname=fontname,
            color=color,
            align=format_info["align"],
        )

        marker = fitz.Rect(rect.x1 - 12, rect.y1 - 10, rect.x1, rect.y1)
        page.insert_textbox(
            marker, "…", fontsize=8, fontname="helv", color=(1, 0, 0),
        )

        self.overflow_count += 1
        return False

    def _insert_without_background(
        self, page, rect, text, fontsize, format_info
    ) -> bool:
        fontname = self.font_manager.get_fontname(
            bold=format_info["is_bold"],
            italic=format_info["is_italic"],
        )
        result = page.insert_textbox(
            rect, text,
            fontsize=max(fontsize * 0.85, MIN_FONTSIZE),
            fontname=fontname,
            color=format_info["color"],
            align=format_info["align"],
        )
        return result >= 0