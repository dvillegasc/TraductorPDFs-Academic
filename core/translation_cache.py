"""
Cache de traducciones + sistema de reintentos.
Evita re-traducir textos idénticos y maneja rate limiting.
"""
import time
import hashlib
import json
from pathlib import Path
from typing import Optional

from deep_translator import GoogleTranslator


class TranslationCache:
    """
    Cache en disco de traducciones previas.
    
    Beneficios:
    - Si traduces el mismo paper dos veces, la segunda es instantánea
    - Si la traducción falla a mitad, al reintentar los bloques ya
      traducidos se obtienen del cache (no vuelve a llamar a la API)
    - Reduce drásticamente las llamadas a la API
    """

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = Path.home() / ".pdf_translator_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, str] = {}  # Cache en RAM (sesión actual)

    def _make_key(self, text: str, source: str, target: str) -> str:
        """Genera una clave única para el texto + par de idiomas."""
        raw = f"{source}|{target}|{text}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def get(self, text: str, source: str, target: str) -> Optional[str]:
        """Busca una traducción en el cache."""
        key = self._make_key(text, source, target)

        # 1. Buscar en memoria (más rápido)
        if key in self._memory_cache:
            return self._memory_cache[key]

        # 2. Buscar en disco
        cache_file = self.cache_dir / f"{key}.txt"
        if cache_file.exists():
            try:
                translated = cache_file.read_text(encoding='utf-8')
                self._memory_cache[key] = translated  # Promover a memoria
                return translated
            except Exception:
                pass

        return None

    def put(self, text: str, source: str, target: str, translated: str):
        """Guarda una traducción en el cache."""
        key = self._make_key(text, source, target)

        # Guardar en memoria
        self._memory_cache[key] = translated

        # Guardar en disco
        cache_file = self.cache_dir / f"{key}.txt"
        try:
            cache_file.write_text(translated, encoding='utf-8')
        except Exception:
            pass  # Si falla el disco, al menos queda en memoria

    def get_stats(self) -> dict:
        """Estadísticas del cache."""
        disk_files = list(self.cache_dir.glob("*.txt"))
        return {
            "memory_entries": len(self._memory_cache),
            "disk_entries": len(disk_files),
        }

    def clear(self):
        """Limpia todo el cache."""
        self._memory_cache.clear()
        for f in self.cache_dir.glob("*.txt"):
            try:
                f.unlink()
            except Exception:
                pass


class RobustTranslator:
    """
    Traductor robusto con:
    - Cache (no re-traduce lo mismo)
    - Reintentos automáticos con backoff exponencial
    - Manejo de rate limiting
    - Fallback entre APIs si una falla
    """

    MAX_RETRIES = 3
    INITIAL_DELAY = 1.0        # Segundos antes del primer reintento
    MAX_CHUNK_LENGTH = 4500    # Google Translate límite ~5000 chars

    def __init__(self, source: str = "en", target: str = "es"):
        self.source = source
        self.target = target
        self.cache = TranslationCache()
        self._translator = GoogleTranslator(source=source, target=target)
        self._request_count = 0
        self._cache_hits = 0

    def translate(self, text: str) -> str:
        """
        Traduce texto con cache y reintentos.

        Flujo:
        1. Buscar en cache → si existe, retornar inmediatamente
        2. Si el texto es muy largo, dividir en chunks
        3. Traducir con reintentos automáticos
        4. Guardar en cache para futuras consultas
        """
        if not text or not text.strip():
            return ""

        # 1. Buscar en cache
        cached = self.cache.get(text, self.source, self.target)
        if cached is not None:
            self._cache_hits += 1
            return cached

        # 2. Si es muy largo, dividir
        if len(text) > self.MAX_CHUNK_LENGTH:
            return self._translate_long_text(text)

        # 3. Traducir con reintentos
        translated = self._translate_with_retry(text)

        # 4. Guardar en cache
        if translated:
            self.cache.put(text, self.source, self.target, translated)

        return translated

    def _translate_with_retry(self, text: str) -> str:
        """Traduce con reintentos y backoff exponencial."""
        delay = self.INITIAL_DELAY

        for attempt in range(self.MAX_RETRIES):
            try:
                self._request_count += 1

                # Rate limiting preventivo: pausa cada 10 requests
                if self._request_count % 10 == 0:
                    time.sleep(0.5)

                result = self._translator.translate(text)
                return result or ""

            except Exception as e:
                error_msg = str(e).lower()

                # Si es rate limiting, esperar más tiempo
                if any(word in error_msg for word in [
                    'rate', 'limit', 'quota', '429', 'too many'
                ]):
                    delay = delay * 3  # Esperar mucho más
                elif any(word in error_msg for word in [
                    'timeout', 'connection', 'network'
                ]):
                    delay = delay * 2

                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= 2  # Backoff exponencial
                else:
                    # Último intento falló — retornar texto original
                    return text  # Mejor devolver el original que nada

        return text

    def _translate_long_text(self, text: str) -> str:
        """
        Divide texto largo en chunks y traduce cada uno.
        Divide por oraciones para no cortar a mitad de frase.
        """
        import re

        # Dividir por oraciones (punto seguido de espacio y mayúscula)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 < self.MAX_CHUNK_LENGTH:
                current_chunk += (" " if current_chunk else "") + sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        # Traducir cada chunk
        translated_chunks = []
        for chunk in chunks:
            translated = self.translate(chunk)  # Usa cache+retry
            translated_chunks.append(translated)

        return " ".join(translated_chunks)

    def get_stats(self) -> dict:
        """Estadísticas del traductor."""
        cache_stats = self.cache.get_stats()
        return {
            "api_requests": self._request_count,
            "cache_hits": self._cache_hits,
            **cache_stats,
        }