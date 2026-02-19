"""
Configuración global de la aplicación.
Centraliza todas las constantes y parámetros ajustables.
"""

# --- Aplicación ---
APP_NAME = "PDF Academic Translator"
APP_VERSION = "3.0.0"
WINDOW_TITLE = "📄 PDF Academic Translator — EN → ES"
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 900

# --- Renderizado PDF ---
BASE_DPI = 150
MIN_ZOOM = 0.25
MAX_ZOOM = 5.0
ZOOM_STEP = 1.25
PAGE_GAP = 20

# --- Traducción ---
DEFAULT_SOURCE_LANG = "en"
DEFAULT_TARGET_LANG = "es"
MIN_TEXT_LENGTH = 3
MAX_FONTSIZE = 14
MIN_FONTSIZE = 4.5
FONTSIZE_REDUCTION_STEPS = 8
FONTSIZE_REDUCTION_FACTOR = 0.90
MAX_RECT_EXPANSION_PTS = 30

# --- Layout ---
HEADER_MARGIN_PTS = 60
FOOTER_MARGIN_PTS = 50

# --- OCR ---
OCR_DPI = 300
OCR_MIN_CONFIDENCE = 30

# --- API ---
TRANSLATION_BATCH_DELAY = 0.1

# --- Fuentes ---
# PyMuPDF built-in fonts no soportan Unicode extendido (griegas, etc.)
# Usamos una fuente del sistema que sí soporte estos caracteres.
# El motor buscará estas fuentes en orden hasta encontrar una disponible.
UNICODE_FONT_PATHS = [
    # Windows
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/arialuni.ttf",      # Arial Unicode MS (ideal)
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/times.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    # macOS
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]

UNICODE_FONT_BOLD_PATHS = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

UNICODE_FONT_ITALIC_PATHS = [
    "C:/Windows/Fonts/ariali.ttf",
    "C:/Windows/Fonts/calibrii.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
]