"""
Sistema de soporte multi-idioma.
Gestiona idiomas disponibles, factores de expansión de texto,
y detección automática de idioma.
"""
from dataclasses import dataclass


@dataclass
class LanguageConfig:
    """Configuración de un idioma soportado."""
    code: str              # Código ISO 639-1 (o variante)
    name_native: str       # Nombre en su propio idioma
    name_spanish: str      # Nombre en español
    name_english: str      # Nombre en inglés
    expansion_factor: float  # Longitud relativa vs inglés (1.0 = igual)
    rtl: bool = False      # Right-to-left
    needs_cjk_font: bool = False  # Requiere fuente CJK


class LanguageManager:
    """Gestiona los idiomas soportados por la aplicación."""

    LANGUAGES = {
        # --- Idiomas occidentales ---
        "en": LanguageConfig("en", "English", "Inglés", "English", 1.00),
        "es": LanguageConfig("es", "Español", "Español", "Spanish", 1.25),
        "pt": LanguageConfig("pt", "Português", "Portugués", "Portuguese", 1.20),
        "fr": LanguageConfig("fr", "Français", "Francés", "French", 1.30),
        "de": LanguageConfig("de", "Deutsch", "Alemán", "German", 1.35),
        "it": LanguageConfig("it", "Italiano", "Italiano", "Italian", 1.15),
        "nl": LanguageConfig("nl", "Nederlands", "Holandés", "Dutch", 1.15),
        "pl": LanguageConfig("pl", "Polski", "Polaco", "Polish", 1.10),
        "tr": LanguageConfig("tr", "Türkçe", "Turco", "Turkish", 1.15),
        "ro": LanguageConfig("ro", "Română", "Rumano", "Romanian", 1.15),
        "sv": LanguageConfig("sv", "Svenska", "Sueco", "Swedish", 1.10),
        "da": LanguageConfig("da", "Dansk", "Danés", "Danish", 1.10),
        "no": LanguageConfig("no", "Norsk", "Noruego", "Norwegian", 1.10),
        "fi": LanguageConfig("fi", "Suomi", "Finlandés", "Finnish", 1.20),
        "cs": LanguageConfig("cs", "Čeština", "Checo", "Czech", 1.10),
        "hu": LanguageConfig("hu", "Magyar", "Húngaro", "Hungarian", 1.20),
        "el": LanguageConfig("el", "Ελληνικά", "Griego", "Greek", 1.15),
        "uk": LanguageConfig("uk", "Українська", "Ucraniano", "Ukrainian", 1.10),
        "ca": LanguageConfig("ca", "Català", "Catalán", "Catalan", 1.20),

        # --- Eslavo ---
        "ru": LanguageConfig("ru", "Русский", "Ruso", "Russian", 1.10),

        # --- CJK ---
        "zh-CN": LanguageConfig(
            "zh-CN", "中文(简体)", "Chino Simplificado",
            "Chinese (Simplified)", 0.60, needs_cjk_font=True
        ),
        "zh-TW": LanguageConfig(
            "zh-TW", "中文(繁體)", "Chino Tradicional",
            "Chinese (Traditional)", 0.60, needs_cjk_font=True
        ),
        "ja": LanguageConfig(
            "ja", "日本語", "Japonés", "Japanese", 0.70,
            needs_cjk_font=True
        ),
        "ko": LanguageConfig(
            "ko", "한국어", "Coreano", "Korean", 0.75,
            needs_cjk_font=True
        ),

        # --- RTL ---
        "ar": LanguageConfig(
            "ar", "العربية", "Árabe", "Arabic", 0.90, rtl=True
        ),
        "he": LanguageConfig(
            "he", "עברית", "Hebreo", "Hebrew", 0.85, rtl=True
        ),
        "fa": LanguageConfig(
            "fa", "فارسی", "Persa", "Persian", 0.90, rtl=True
        ),

        # --- Índico ---
        "hi": LanguageConfig("hi", "हिन्दी", "Hindi", "Hindi", 1.10),
        "bn": LanguageConfig("bn", "বাংলা", "Bengalí", "Bengali", 1.10),

        # --- Otros ---
        "vi": LanguageConfig("vi", "Tiếng Việt", "Vietnamita", "Vietnamese", 1.20),
        "th": LanguageConfig("th", "ไทย", "Tailandés", "Thai", 0.90),
        "id": LanguageConfig("id", "Bahasa Indonesia", "Indonesio", "Indonesian", 1.15),
        "ms": LanguageConfig("ms", "Bahasa Melayu", "Malayo", "Malay", 1.15),
    }

    # Idiomas más usados como ORIGEN en papers académicos
    COMMON_SOURCE_LANGS = ["en", "zh-CN", "de", "fr", "es", "pt", "ja", "ko", "ru"]

    # Idiomas más solicitados como DESTINO
    COMMON_TARGET_LANGS = [
        "es", "pt", "fr", "de", "it", "zh-CN", "ja", "ko",
        "ru", "ar", "hi", "tr", "pl", "nl",
    ]

    @classmethod
    def get_language(cls, code: str) -> LanguageConfig | None:
        return cls.LANGUAGES.get(code)

    @classmethod
    def get_expansion_factor(cls, target_lang: str) -> float:
        lang = cls.LANGUAGES.get(target_lang)
        return lang.expansion_factor if lang else 1.20

    @classmethod
    def get_source_languages(cls) -> list[tuple[str, str]]:
        """Retorna lista de (código, nombre) para idiomas origen."""
        return [
            (code, f"{cls.LANGUAGES[code].name_native} ({cls.LANGUAGES[code].name_english})")
            for code in cls.COMMON_SOURCE_LANGS
            if code in cls.LANGUAGES
        ]

    @classmethod
    def get_target_languages(cls) -> list[tuple[str, str]]:
        """Retorna lista de (código, nombre) para idiomas destino."""
        return [
            (code, f"{cls.LANGUAGES[code].name_native} ({cls.LANGUAGES[code].name_english})")
            for code in cls.COMMON_TARGET_LANGS
            if code in cls.LANGUAGES
        ]

    @classmethod
    def detect_language(cls, text: str) -> str:
        """Detecta el idioma de un texto automáticamente."""
        try:
            from langdetect import detect
            detected = detect(text)
            # langdetect retorna 'zh-cn' → normalizar a 'zh-CN'
            if detected == 'zh-cn':
                return 'zh-CN'
            if detected == 'zh-tw':
                return 'zh-TW'
            return detected
        except Exception:
            return "en"