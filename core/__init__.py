"""
Core — Motor de traducción de PDFs académicos.
"""
from core.translator_engine import TranslatorEngine
from core.pdf_analyzer import PDFAnalyzer
from core.formula_detector import FormulaDetector
from core.glossary import Glossary
from core.layout_engine import LayoutEngine
from core.languages import LanguageManager
from core.translation_cache import TranslationCache, RobustTranslator
from core.table_detector import TableDetector, TableRegion
from core.font_manager import FontManager