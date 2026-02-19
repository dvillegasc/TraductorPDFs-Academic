"""
Gestor de fuentes Unicode para PyMuPDF.

Problema: Las fuentes built-in de PyMuPDF (helv, heit, hebo) NO soportan
caracteres Unicode extendidos como letras griegas (θ, α, β), operadores
matemáticos (≤, ≥, ≈) ni muchos caracteres de idiomas no-latinos.

Solución: Registrar fuentes del sistema operativo que SÍ soporten
estos caracteres y usarlas al insertar texto en el PDF.
"""
import os
from pathlib import Path
from typing import Optional

import fitz

from config import (
    UNICODE_FONT_PATHS,
    UNICODE_FONT_BOLD_PATHS,
    UNICODE_FONT_ITALIC_PATHS,
)


class FontManager:
    """
    Busca y registra fuentes Unicode del sistema operativo.
    
    Uso:
        fm = FontManager()
        fontname = fm.register_font(page, bold=False, italic=False)
        page.insert_textbox(rect, text, fontname=fontname, ...)
    """

    # Nombres internos que usaremos en PyMuPDF
    FONT_NAME_REGULAR = "unic"
    FONT_NAME_BOLD = "unicb"
    FONT_NAME_ITALIC = "unici"

    def __init__(self):
        self._regular_path: Optional[str] = None
        self._bold_path: Optional[str] = None
        self._italic_path: Optional[str] = None
        self._initialized = False

        self._find_fonts()

    def _find_fonts(self):
        """Busca fuentes Unicode disponibles en el sistema."""
        # Regular
        for path in UNICODE_FONT_PATHS:
            if os.path.exists(path):
                self._regular_path = path
                break

        # Bold
        for path in UNICODE_FONT_BOLD_PATHS:
            if os.path.exists(path):
                self._bold_path = path
                break

        # Italic
        for path in UNICODE_FONT_ITALIC_PATHS:
            if os.path.exists(path):
                self._italic_path = path
                break

        # Si no encontramos bold/italic, usar regular para todo
        if not self._bold_path:
            self._bold_path = self._regular_path
        if not self._italic_path:
            self._italic_path = self._regular_path

        self._initialized = True

    @property
    def has_unicode_font(self) -> bool:
        """Retorna True si se encontró al menos una fuente Unicode."""
        return self._regular_path is not None

    def get_font_info(self) -> str:
        """Info de diagnóstico sobre las fuentes encontradas."""
        lines = ["Fuentes Unicode:"]
        lines.append(f"  Regular: {self._regular_path or 'NO ENCONTRADA'}")
        lines.append(f"  Bold:    {self._bold_path or 'NO ENCONTRADA'}")
        lines.append(f"  Italic:  {self._italic_path or 'NO ENCONTRADA'}")
        return "\n".join(lines)

    def register_font(
        self,
        page: fitz.Page,
        bold: bool = False,
        italic: bool = False,
    ) -> str:
        """
        Registra la fuente apropiada en la página y retorna su nombre interno.
        
        Debe llamarse ANTES de insert_textbox en cada página nueva.
        
        Args:
            page: La página de PyMuPDF donde se insertará texto
            bold: Si necesitamos la variante bold
            italic: Si necesitamos la variante italic
        
        Returns:
            Nombre interno de la fuente (para usar en fontname=)
        """
        if bold and self._bold_path:
            font_path = self._bold_path
            font_name = self.FONT_NAME_BOLD
        elif italic and self._italic_path:
            font_path = self._italic_path
            font_name = self.FONT_NAME_ITALIC
        elif self._regular_path:
            font_path = self._regular_path
            font_name = self.FONT_NAME_REGULAR
        else:
            # Fallback a Helvetica si no hay fuente Unicode
            return "helv"

        try:
            # Registrar la fuente en la página
            page.insert_font(
                fontname=font_name,
                fontfile=font_path,
            )
            return font_name
        except Exception:
            # Si falla el registro, usar Helvetica como fallback
            return "helv"

    def register_all_variants(self, page: fitz.Page):
        """
        Registra regular, bold e italic en una página.
        Llamar una vez al inicio de cada página.
        """
        self.register_font(page, bold=False, italic=False)
        self.register_font(page, bold=True, italic=False)
        self.register_font(page, bold=False, italic=True)

    def get_fontname(self, bold: bool = False, italic: bool = False) -> str:
        """Retorna el nombre interno de la fuente según el estilo."""
        if not self.has_unicode_font:
            if bold:
                return "hebo"
            elif italic:
                return "heit"
            return "helv"

        if bold:
            return self.FONT_NAME_BOLD
        elif italic:
            return self.FONT_NAME_ITALIC
        return self.FONT_NAME_REGULAR