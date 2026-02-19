"""
Hilo de trabajo para la traducción.
Ejecuta la traducción sin bloquear la interfaz gráfica.
"""
from PyQt6.QtCore import QThread, pyqtSignal

from core.translator_engine import TranslatorEngine
from core.pdf_analyzer import PDFDiagnostic


class TranslationWorker(QThread):
    """
    Hilo que ejecuta la traducción en background.
    
    Señales:
    - progress(int): porcentaje 0-100
    - status(str): mensaje de estado actual
    - analysis_done(PDFDiagnostic): resultado del análisis previo
    - finished(str): ruta del PDF traducido
    - error(str): mensaje de error
    - stats(str): resumen de estadísticas
    """
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    analysis_done = pyqtSignal(object)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    stats = pyqtSignal(str)

    def __init__(
        self,
        input_path: str,
        source_lang: str = "en",
        target_lang: str = "es",
        apply_ocr: bool = False,
        glossary_areas: list[str] = None,
    ):
        super().__init__()
        self.input_path = input_path
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.apply_ocr = apply_ocr
        self.glossary_areas = glossary_areas
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            engine = TranslatorEngine(
                source_lang=self.source_lang,
                target_lang=self.target_lang,
                glossary_areas=self.glossary_areas,
            )

            self.status.emit("Analizando PDF...")
            diagnostic = engine.analyze(self.input_path)
            self.analysis_done.emit(diagnostic)

            if not diagnostic.can_translate and not self.apply_ocr:
                self.error.emit(
                    "Este PDF no se puede traducir directamente.\n"
                    + "\n".join(diagnostic.warnings)
                )
                return

            output_path = engine.translate(
                input_path=self.input_path,
                apply_ocr=self.apply_ocr,
                progress_callback=self._on_progress,
                cancel_check=lambda: self._cancelled,
            )

            if self._cancelled:
                self.status.emit("Traducción cancelada.")
                return

            if not output_path:
                self.error.emit("La traducción no produjo resultado.")
                return

            self.stats.emit(engine.get_stats_summary())
            self.status.emit("¡Traducción completada!")
            self.finished.emit(output_path)

        except Exception as e:
            self.error.emit(f"Error durante la traducción:\n{str(e)}")

    def _on_progress(self, percent: int, message: str):
        self.progress.emit(percent)
        self.status.emit(message)