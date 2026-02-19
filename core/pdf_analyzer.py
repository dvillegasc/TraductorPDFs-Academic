"""
Analizador de PDFs.
Diagnostica el tipo, complejidad y traducibilidad de un PDF.
"""
import fitz
from dataclasses import dataclass, field


@dataclass
class PDFDiagnostic:
    """Resultado del diagnóstico de un PDF."""
    file_path: str
    pdf_type: str              # 'digital', 'scanned', 'hybrid'
    total_pages: int = 0
    pages_with_text: int = 0
    pages_image_only: int = 0
    pages_hybrid: int = 0
    total_characters: int = 0
    total_images: int = 0
    needs_ocr: bool = False
    has_tables: bool = False
    has_multi_columns: bool = False
    has_forms: bool = False
    is_encrypted: bool = False
    complexity: str = "low"    # 'low', 'medium', 'high'
    can_translate: bool = True
    warnings: list[str] = field(default_factory=list)
    estimated_time_seconds: int = 0


class PDFAnalyzer:
    """Analiza un PDF antes de traducirlo."""

    # Umbral mínimo de caracteres para considerar que una página tiene texto
    MIN_CHARS_FOR_TEXT = 50

    @classmethod
    def analyze(cls, path: str) -> PDFDiagnostic:
        """
        Analiza un PDF y retorna un diagnóstico completo.
        Debe llamarse ANTES de iniciar cualquier traducción.
        """
        diag = PDFDiagnostic(file_path=path, pdf_type="digital")

        try:
            doc = fitz.open(path)
        except Exception as e:
            diag.can_translate = False
            diag.warnings.append(f"❌ No se puede abrir el PDF: {e}")
            return diag

        # Verificar encriptación
        if doc.is_encrypted:
            diag.is_encrypted = True
            diag.can_translate = False
            diag.warnings.append(
                "🔒 El PDF está protegido con contraseña. "
                "No se puede traducir sin desencriptarlo primero."
            )
            doc.close()
            return diag

        diag.total_pages = len(doc)

        for page in doc:
            text = page.get_text().strip()
            images = page.get_images()
            chars = len(text)

            diag.total_characters += chars
            diag.total_images += len(images)

            if chars >= cls.MIN_CHARS_FOR_TEXT:
                if len(images) > 0 and chars < 200:
                    diag.pages_hybrid += 1
                else:
                    diag.pages_with_text += 1
            else:
                if len(images) > 0:
                    diag.pages_image_only += 1

            # Detectar tablas (heurística: muchos bloques alineados)
            blocks = page.get_text("blocks")
            if len(blocks) > 20:
                diag.has_tables = True

            # Detectar múltiples columnas
            text_blocks = [b for b in blocks if b[6] == 0]
            if text_blocks:
                x_positions = [round(b[0], -1) for b in text_blocks]
                unique_x = len(set(x_positions))
                if unique_x >= 2:
                    diag.has_multi_columns = True

            # Detectar formularios
            if page.widgets():
                diag.has_forms = True

        doc.close()

        # Determinar tipo de PDF
        ratio_image = diag.pages_image_only / max(diag.total_pages, 1)
        ratio_hybrid = diag.pages_hybrid / max(diag.total_pages, 1)

        if ratio_image > 0.8:
            diag.pdf_type = "scanned"
            diag.needs_ocr = True
        elif ratio_image > 0.2 or ratio_hybrid > 0.3:
            diag.pdf_type = "hybrid"
            diag.needs_ocr = True
        else:
            diag.pdf_type = "digital"
            diag.needs_ocr = False

        # Complejidad
        complexity_score = 0
        if diag.has_tables:
            complexity_score += 1
        if diag.has_multi_columns:
            complexity_score += 1
        if diag.needs_ocr:
            complexity_score += 1
        if diag.total_pages > 30:
            complexity_score += 1

        if complexity_score >= 3:
            diag.complexity = "high"
        elif complexity_score >= 1:
            diag.complexity = "medium"
        else:
            diag.complexity = "low"

        # Traducibilidad
        if diag.pdf_type == "scanned":
            diag.can_translate = False  # Sin OCR no se puede
        elif diag.is_encrypted:
            diag.can_translate = False
        else:
            diag.can_translate = True

        # Generar advertencias
        diag.warnings = cls._generate_warnings(diag)

        # Estimar tiempo
        time_per_page = 8  # segundos base
        if diag.needs_ocr:
            time_per_page += 5
        if diag.has_tables:
            time_per_page += 2
        diag.estimated_time_seconds = diag.total_pages * time_per_page

        return diag

    @staticmethod
    def _generate_warnings(diag: PDFDiagnostic) -> list[str]:
        warnings = []
        if diag.pdf_type == "scanned":
            warnings.append(
                "⚠️ PDF escaneado (imagen). Se requiere OCR para extraer "
                "el texto. Activa la opción 'Aplicar OCR' antes de traducir."
            )
        elif diag.pdf_type == "hybrid":
            warnings.append(
                "⚠️ PDF híbrido: mezcla texto digital e imágenes. "
                "Algunas secciones podrían no traducirse."
            )
        if diag.has_tables:
            warnings.append(
                "⚠️ Se detectaron tablas. Su formato podría alterarse."
            )
        if diag.has_multi_columns:
            warnings.append(
                "ℹ️ Layout de múltiples columnas detectado."
            )
        if diag.total_pages > 50:
            warnings.append(
                f"ℹ️ Documento extenso ({diag.total_pages} páginas). "
                f"Tiempo estimado: ~{diag.estimated_time_seconds // 60} min."
            )
        if diag.has_forms:
            warnings.append(
                "ℹ️ Se detectaron formularios interactivos. "
                "Los campos de formulario no se traducirán."
            )
        return warnings