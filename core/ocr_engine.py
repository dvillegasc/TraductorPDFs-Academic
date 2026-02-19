"""
Motor OCR para PDFs escaneados.
Convierte imágenes a texto extraíble usando Tesseract.
"""
import io
import fitz
from config import OCR_DPI, OCR_MIN_CONFIDENCE


class OCREngine:
    """
    Aplica OCR a PDFs escaneados para hacerlos traducibles.
    
    Flujo:
    1. Renderizar cada página como imagen a alta resolución
    2. Aplicar Tesseract OCR para extraer texto + posiciones
    3. Crear un nuevo PDF con la imagen original + capa de texto
    4. El nuevo PDF es procesable por el motor de traducción normal
    """

    # Mapeo de códigos de idioma de la app → códigos de Tesseract
    LANG_MAP = {
        "en": "eng",
        "es": "spa",
        "pt": "por",
        "fr": "fra",
        "de": "deu",
        "it": "ita",
        "nl": "nld",
        "pl": "pol",
        "ru": "rus",
        "zh-CN": "chi_sim",
        "zh-TW": "chi_tra",
        "ja": "jpn",
        "ko": "kor",
        "ar": "ara",
        "hi": "hin",
        "tr": "tur",
    }

    @classmethod
    def is_available(cls) -> bool:
        """Verifica si Tesseract está instalado y disponible."""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @classmethod
    def apply_ocr(
        cls,
        input_path: str,
        output_path: str,
        language: str = "en",
        progress_callback=None,
    ) -> str:
        """
        Aplica OCR a un PDF escaneado y genera un PDF con texto extraíble.
        
        Args:
            input_path: Ruta del PDF escaneado
            output_path: Ruta donde guardar el PDF con texto
            language: Código de idioma del texto en el PDF
            progress_callback: Función callback(percent, message)
        
        Returns:
            Ruta del PDF generado con capa de texto
        """
        import pytesseract
        from PIL import Image

        tess_lang = cls.LANG_MAP.get(language, "eng")

        doc_input = fitz.open(input_path)
        doc_output = fitz.open()
        total_pages = len(doc_input)

        for page_idx, page in enumerate(doc_input):
            if progress_callback:
                pct = int((page_idx / total_pages) * 100)
                progress_callback(pct, f"OCR página {page_idx + 1}/{total_pages}")

            # Renderizar página como imagen de alta resolución
            zoom = OCR_DPI / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))

            # Obtener datos OCR con posiciones (bounding boxes)
            ocr_data = pytesseract.image_to_data(
                img, lang=tess_lang, output_type=pytesseract.Output.DICT
            )

            # Crear nueva página con imagen original
            new_page = doc_output.new_page(
                width=page.rect.width, height=page.rect.height
            )
            new_page.insert_image(new_page.rect, pixmap=pix)

            # Escala de coordenadas: imagen OCR → coordenadas PDF
            scale_x = page.rect.width / img.width
            scale_y = page.rect.height / img.height

            # Agregar capa de texto sobre la imagen
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                conf = int(ocr_data['conf'][i])

                if text and conf >= OCR_MIN_CONFIDENCE:
                    x = ocr_data['left'][i] * scale_x
                    y = ocr_data['top'][i] * scale_y
                    w = ocr_data['width'][i] * scale_x
                    h = ocr_data['height'][i] * scale_y

                    rect = fitz.Rect(x, y, x + w, y + h)
                    fontsize = max(h * 0.7, 4)

                    # Texto con render_mode=3 = invisible
                    # Se puede seleccionar/buscar pero no se ve
                    new_page.insert_textbox(
                        rect, text,
                        fontsize=fontsize,
                        fontname="helv",
                        render_mode=3,
                    )

        doc_output.save(output_path)
        doc_output.close()
        doc_input.close()

        if progress_callback:
            progress_callback(100, "OCR completado")

        return output_path