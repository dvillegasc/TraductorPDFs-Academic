"""
Motor principal de traducción — Versión 3.0
Integra detección de tablas, protección de fórmulas y segmentación.
"""
import time
import tempfile
from typing import Callable, Optional

import fitz

from config import (
    DEFAULT_SOURCE_LANG, DEFAULT_TARGET_LANG,
    MIN_TEXT_LENGTH,
)
from core.formula_detector import FormulaDetector
from core.glossary import Glossary
from core.layout_engine import LayoutEngine
from core.pdf_analyzer import PDFAnalyzer, PDFDiagnostic
from core.ocr_engine import OCREngine
from core.table_detector import TableDetector
from core.translation_cache import RobustTranslator


class TranslatorEngine:
    """
    Motor principal v3.0
    
    Flujo por página:
    1. Detectar zonas de tablas → marcar como NO-TOCAR
    2. Extraer bloques de texto
    3. Clasificar cada bloque:
       - Tabla → SKIP (no tocar)
       - Header/footer → SKIP
       - Fórmula pura → SKIP + registrar posición como zona protegida
       - Texto narrativo → TRADUCIR con segmentación inteligente
    4. Insertar texto traducido respetando zonas protegidas
    """

    def __init__(
        self,
        source_lang: str = DEFAULT_SOURCE_LANG,
        target_lang: str = DEFAULT_TARGET_LANG,
        glossary_areas: list[str] = None,
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.formula_detector = FormulaDetector()
        self.glossary = Glossary(areas_activas=glossary_areas)
        self.layout_engine = LayoutEngine()
        self.translator = RobustTranslator(source=source_lang, target=target_lang)

        self.stats = {
            "total_blocks": 0,
            "translated_blocks": 0,
            "skipped_formulas": 0,
            "skipped_headers": 0,
            "skipped_tables": 0,
            "skipped_short": 0,
            "overflow_blocks": 0,
            "errors": 0,
        }

    def analyze(self, input_path: str) -> PDFDiagnostic:
        return PDFAnalyzer.analyze(input_path)

    def translate(
        self,
        input_path: str,
        output_path: str = None,
        apply_ocr: bool = False,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> str:
        if output_path is None:
            output_path = tempfile.mktemp(suffix="_traducido.pdf")

        self.stats = {k: 0 for k in self.stats}
        self.layout_engine.overflow_count = 0

        # --- OCR si es necesario ---
        working_path = input_path
        if apply_ocr:
            if not OCREngine.is_available():
                raise RuntimeError(
                    "Tesseract OCR no está instalado.\n"
                    "  - Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
                    "  - macOS: brew install tesseract\n"
                    "  - Linux: sudo apt install tesseract-ocr"
                )

            if progress_callback:
                progress_callback(0, "Aplicando OCR...")

            ocr_output = tempfile.mktemp(suffix="_ocr.pdf")
            OCREngine.apply_ocr(
                input_path=input_path,
                output_path=ocr_output,
                language=self.source_lang,
                progress_callback=lambda p, m: (
                    progress_callback(int(p * 0.2), f"OCR: {m}")
                    if progress_callback else None
                ),
            )
            working_path = ocr_output

        # --- Abrir PDF ---
        doc = fitz.open(working_path)
        total_pages = len(doc)

        # --- Detectar tablas en TODO el documento primero ---
        if progress_callback:
            progress_callback(
                20 if apply_ocr else 0,
                "Detectando tablas y fórmulas..."
            )

        all_tables = TableDetector.detect_all_tables(doc)
        total_tables = sum(len(t) for t in all_tables.values())

        if progress_callback:
            base = 25 if apply_ocr else 5
            progress_callback(
                base,
                f"Encontradas {total_tables} tablas. Iniciando traducción..."
            )

        # --- Traducir página por página ---
        for page_idx, page in enumerate(doc):
            if cancel_check and cancel_check():
                doc.close()
                return ""

            if progress_callback:
                base = 25 if apply_ocr else 5
                remaining = 95 - base
                pct = base + int(((page_idx) / total_pages) * remaining)
                progress_callback(
                    pct,
                    f"Traduciendo página {page_idx + 1} de {total_pages}..."
                )

            # Configurar tablas para esta página
            page_tables = all_tables.get(page_idx, [])
            self._translate_page(page, page_tables)

        # --- Guardar ---
        doc.save(output_path)
        doc.close()

        self.stats["overflow_blocks"] = self.layout_engine.overflow_count

        if progress_callback:
            progress_callback(100, "¡Traducción completada!")

        return output_path

    def _translate_page(self, page: fitz.Page, table_regions: list):
        """Traduce una página respetando tablas y fórmulas."""
        page_rect = page.rect

        # Limpiar estado de la página anterior
        self.layout_engine.clear_page_state()
        self.layout_engine.set_table_regions(table_regions)

        # REGISTRAR FUENTES UNICODE para esta página
        self.layout_engine.register_fonts_for_page(page)

        blocks = page.get_text("blocks")

        # --- PRIMER PASADA: Identificar fórmulas ---
        formula_blocks = []
        text_blocks = []

        for block in blocks:
            original_text = block[4].strip()
            is_image = block[6] == 1
            block_rect = fitz.Rect(block[:4])

            if not original_text or is_image:
                continue

            if self.formula_detector.es_no_traducible(original_text):
                self.layout_engine.add_formula_rect(block_rect)
                formula_blocks.append(block)
            else:
                text_blocks.append(block)

        self.stats["skipped_formulas"] += len(formula_blocks)

        occupied_zones = self.layout_engine.get_occupied_zones(page)

        # --- SEGUNDA PASADA: Traducir texto ---
        for block in text_blocks:
            self.stats["total_blocks"] += 1

            original_text = block[4].strip()
            block_rect = fitz.Rect(block[:4])

            if self.layout_engine.is_header_or_footer(block_rect, page_rect):
                self.stats["skipped_headers"] += 1
                continue

            if self.layout_engine.is_inside_table(block_rect):
                self.stats["skipped_tables"] += 1
                continue

            clean_text = original_text.replace('\n', ' ').strip()
            if len(clean_text) < MIN_TEXT_LENGTH:
                self.stats["skipped_short"] += 1
                continue

            try:
                translated = self._translate_text(clean_text)
                if not translated:
                    continue

                format_info = self.layout_engine.extract_block_format(
                    page, block_rect
                )

                self.layout_engine.insert_translated_text(
                    page=page,
                    rect=block_rect,
                    text=translated,
                    format_info=format_info,
                    occupied_zones=occupied_zones,
                )

                self.stats["translated_blocks"] += 1

            except Exception:
                self.stats["errors"] += 1
                continue

    def _translate_text(self, text: str) -> str:
        """
        Traduce texto con segmentación inteligente:
        1. Separar partes traducibles de fórmulas/citas inline
        2. Proteger términos del glosario
        3. Traducir con cache + reintentos
        4. Re-ensamblar todo
        """
        segments = self.formula_detector.extraer_segmentos(text)

        translated_parts = []

        for segment in segments:
            if not segment["translate"]:
                translated_parts.append(segment["text"])
            else:
                part = segment["text"]
                if len(part.strip()) < 2:
                    translated_parts.append(part)
                    continue

                protected = self.glossary.proteger_terminos(part)
                translated = self.translator.translate(protected)

                if translated:
                    translated = self.glossary.restaurar_terminos(translated)
                    translated = self.glossary.corregir_post_traduccion(translated)
                    translated_parts.append(translated)
                else:
                    translated_parts.append(part)

        return "".join(translated_parts)

    def get_stats_summary(self) -> str:
        s = self.stats
        t_stats = self.translator.get_stats()
        total = s["total_blocks"] + s["skipped_formulas"]
        if total == 0:
            return "No se procesaron bloques."

        lines = [
            "📊 Resumen de traducción:",
            f"   Bloques analizados:     {total}",
            f"   ✅ Traducidos:           {s['translated_blocks']}",
            f"   🔢 Fórmulas protegidas:  {s['skipped_formulas']}",
            f"   📋 Tablas protegidas:    {s['skipped_tables']}",
            f"   📄 Headers/footers:      {s['skipped_headers']}",
            f"   📏 Muy cortos:           {s['skipped_short']}",
            f"   ⚠️  Overflow:             {s['overflow_blocks']}",
            f"   ❌ Errores:              {s['errors']}",
            "",
            "🌐 API de traducción:",
            f"   Llamadas a la API:      {t_stats['api_requests']}",
            f"   Hits de cache:          {t_stats['cache_hits']}",
            f"   Entradas en cache:      {t_stats['disk_entries']} (disco)",
        ]
        return "\n".join(lines)