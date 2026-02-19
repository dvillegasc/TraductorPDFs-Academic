"""
Detector de fórmulas v4.0
==========================
Cambios vs v3:
- Protege letras aisladas seguidas de paréntesis: f(x), g(x,θ), E(Y)
- Detecta bloques LaTeX crudo ($...$, \frac, \sqrt) de forma más robusta
- Mejor segmentación de fórmulas inline vs texto narrativo
"""
import re


class FormulaDetector:
    """
    Detecta bloques que NO deben traducirse.
    
    REGLA DE ORO: Si tiene más de 4 palabras comunes inglesas → TRADUCIR.
    Si es una fórmula pura, variable aislada o LaTeX → NO TOCAR.
    """

    PURE_MATH_SYMBOLS = set('∑∫∂√∞≡∝∈∉⊂⊃⊆⊇∪∩∧∨¬∀∃∇⊗⊕⊥∥⊞⊟⊠∅')
    GREEK_LETTERS = set('αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΠΣΦΨΩ')

    COMMON_WORDS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'shall', 'must',
        'of', 'in', 'to', 'for', 'with', 'on', 'at', 'from', 'by',
        'about', 'as', 'into', 'through', 'during', 'before', 'after',
        'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both',
        'that', 'this', 'these', 'those', 'it', 'its', 'they', 'them',
        'we', 'our', 'he', 'she', 'his', 'her', 'who', 'which',
        'what', 'where', 'when', 'how', 'why', 'if', 'then', 'than',
        'also', 'more', 'most', 'such', 'each', 'every', 'all',
        'some', 'any', 'no', 'only', 'very', 'just', 'even',
        'new', 'used', 'one', 'two', 'first', 'last',
        'study', 'paper', 'method', 'results', 'data', 'model',
        'analysis', 'based', 'proposed', 'shown', 'shows', 'show',
        'table', 'figure', 'section', 'however', 'therefore',
        'thus', 'hence', 'moreover', 'furthermore', 'although',
        'since', 'because', 'while', 'whereas', 'between',
        'given', 'using', 'following', 'according', 'defined',
        'distribution', 'function', 'parameter', 'value', 'values',
        'equation', 'variable', 'variables', 'number',
        'probability', 'random', 'sample', 'test', 'hypothesis',
        'estimate', 'estimated', 'estimation', 'error', 'mean',
        'standard', 'deviation', 'variance', 'confidence',
        'statistical', 'statistics', 'significant', 'significance',
        'assume', 'assumed', 'assumption', 'consider', 'considered',
        'obtained', 'observed', 'applied', 'application',
        'respectively', 'corresponding', 'particular', 'general',
        'let', 'denotes', 'denote', 'represents',
        'can', 'which', 'when', 'where', 'there', 'here',
        'note', 'noted', 'above', 'below', 'see', 'see',
        'order', 'case', 'cases', 'other', 'another',
        'same', 'different', 'similar', 'known', 'well',
    }

    MIN_COMMON_WORDS_FOR_NARRATIVE = 4

    def __init__(self):
        # LaTeX: bloques completos de ecuaciones
        self._pat_latex_block = re.compile(
            r'(?:'
            r'\\begin\{(?:equation|align|gather|multline|eqnarray|array|matrix|pmatrix|bmatrix|cases)\}|'
            r'\$\$[^$]+\$\$|'
            r'\\\[.+?\\\]'
            r')',
            re.DOTALL,
        )

        # LaTeX inline: $...$
        self._pat_latex_inline = re.compile(r'\$[^$]+\$')

        # Comandos LaTeX comunes
        self._pat_latex_commands = re.compile(
            r'\\(?:frac|sqrt|sum|int|prod|lim|log|ln|sin|cos|tan|exp|'
            r'begin|end|left|right|big|Big|bigg|Bigg|'
            r'mathbb|mathbf|mathrm|mathcal|text|textbf|'
            r'hat|bar|tilde|vec|dot|overline|underline|overbrace|underbrace|'
            r'alpha|beta|gamma|delta|epsilon|theta|lambda|mu|sigma|phi|omega|'
            r'Gamma|Delta|Theta|Lambda|Sigma|Phi|Psi|Omega|'
            r'partial|nabla|infty|forall|exists|emptyset|'
            r'in|notin|subset|supset|cup|cap|'
            r'leq|geq|neq|approx|equiv|sim|propto|'
            r'times|cdot|otimes|oplus|'
            r'quad|qquad|hspace|backslash|'
            r'label|ref|eqref|cite)\b'
        )

        # Funciones matemáticas: f(x), g(x,θ), E(Y), P(X>x), h(·)
        self._pat_math_function = re.compile(
            r'^[a-zA-Z]\s*\([^)]*\)\s*$'
        )

        # Variable aislada con subíndice/superíndice
        self._pat_variable = re.compile(
            r'^[a-zA-Z](?:_\{?[^}]*\}?|\^[{0-9])[^a-zA-Z]*$'
        )

        # Número de ecuación
        self._pat_eq_number = re.compile(
            r'^(?:Eq\.?\s*)?\([\divxlc]+(?:\.\d+)*[a-z]?\)$'
        )

        # Citas bibliográficas
        self._pat_citation = re.compile(r'\[\d+(?:\s*[-–,]\s*\d+)*\]')

        # Código de programación
        self._pat_code = re.compile(
            r'(?:def\s+\w+\s*\(|class\s+\w+[:(]|import\s+\w+|'
            r'from\s+\w+\s+import|>>>|return\s+\w+|print\s*\()'
        )

    def es_no_traducible(self, texto: str) -> bool:
        """
        Determina si un bloque NO debe traducirse.
        """
        if not texto or not texto.strip():
            return True

        t = texto.strip()

        # ============================================
        # PASO 1: ¿Es claramente texto narrativo?
        # Si sí → TRADUCIR, no seguir evaluando
        # ============================================
        if self._is_narrative_text(t):
            return False

        # ============================================
        # PASO 2: Filtros para fórmulas/código PUROS
        # ============================================

        # 2a. Contiene comandos LaTeX (\frac, \sqrt, etc.)
        if self._pat_latex_commands.search(t):
            # PERO: si también tiene muchas palabras normales, es texto mixto
            if self._count_common_words(t) >= 6:
                return False  # Texto que menciona LaTeX
            return True  # LaTeX puro → NO TOCAR

        # 2b. Bloque LaTeX completo ($$...$$, \begin{equation})
        if self._pat_latex_block.search(t):
            return True

        # 2c. Función matemática aislada: f(x), g(x,θ), E(Y), P(X)
        if self._pat_math_function.match(t):
            return True

        # 2d. Variable aislada con sub/superíndice: x_i, x^2
        if self._pat_variable.match(t):
            return True

        # 2e. Número de ecuación: (1), Eq. (4)
        if self._pat_eq_number.match(t):
            return True

        # 2f. Código de programación
        if self._pat_code.search(t):
            if self._count_common_words(t) >= 6:
                return False
            return True

        # 2g. Solo símbolos matemáticos puros
        if self._is_pure_math(t):
            return True

        # 2h. Texto ultra-corto sin palabras reales (< 4 chars)
        if len(t) < 4 and not any(c.isalpha() and c.isascii() for c in t):
            return True

        # 2i. Letra aislada o variable corta: "x", "Y", "n", "θ"
        stripped = t.strip('.,;: ')
        if len(stripped) <= 2 and not stripped.lower() in {'a', 'i', 'an', 'or', 'no', 'so', 'do', 'if', 'he', 'we', 'my', 'me', 'us', 'am', 'as', 'at', 'be', 'by', 'go', 'in', 'is', 'it', 'of', 'on', 'to', 'up'}:
            return True

        # 2j. Solo números y puntuación
        if re.fullmatch(r'[\d\s.,;:!?\-–—()]+', t):
            return True

        # ============================================
        # PASO 3: En caso de duda → TRADUCIR
        # ============================================
        return False

    def _is_narrative_text(self, texto: str) -> bool:
        """Un texto es narrativo si tiene suficientes palabras comunes."""
        common_count = self._count_common_words(texto)

        if common_count >= self.MIN_COMMON_WORDS_FOR_NARRATIVE:
            return True

        if (len(texto) > 50 and
            texto[0].isupper() and
            ' ' in texto and
            common_count >= 2):
            return True

        if len(texto) > 100 and texto.count(' ') > 10:
            return True

        return False

    def _count_common_words(self, texto: str) -> int:
        """Cuenta palabras comunes, ignorando citas y math inline."""
        cleaned = self._pat_citation.sub('', texto)
        cleaned = re.sub(r'\$[^$]*\$', '', cleaned)
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        words = cleaned.lower().split()
        return sum(1 for w in words if w in self.COMMON_WORDS)

    def _is_pure_math(self, texto: str) -> bool:
        """Solo True si el texto es PURAMENTE matemático."""
        if self._count_common_words(texto) >= 2:
            return False

        pure_count = sum(1 for c in texto if c in self.PURE_MATH_SYMBOLS)
        if pure_count >= 2 and len(texto) < 80:
            return True

        math_ops = set('=<>≤≥≈≠±∓×÷^_{}\\|~')
        op_count = sum(1 for c in texto if c in math_ops)
        total = len(texto.replace(' ', ''))
        if total > 0 and op_count / total > 0.35:
            if self._count_common_words(texto) >= 2:
                return False
            return True

        return False

    def extraer_segmentos(self, texto: str) -> list[dict]:
        """
        Segmenta texto mixto: partes traducibles vs no-traducibles.
        
        Protege:
        - Inline LaTeX: $...$
        - Citas: [1], [1-3]
        - Funciones matemáticas inline: f(x), E(Y), P(X>x)
        - Variables griegas aisladas: θ, α, β
        - URLs y DOIs
        """
        segments = []

        # Patrones de contenido a preservar (orden importa)
        preserve_patterns = [
            r'\$[^$]+\$',                              # $inline math$
            r'\\\([^)]+\\\)',                           # \(inline math\)
            r'(?<!\w)[a-zA-Z]\s*\([^)]{1,30}\)',       # f(x), g(x,θ), E(Y)
            r'\[\d+(?:\s*[-–,]\s*\d+)*\]',             # [1], [1-3]
            r'(?:doi|DOI)\s*:\s*\S+',                  # DOI
            r'https?://\S+',                           # URLs
        ]

        # Patrón para letras griegas aisladas (rodeadas de espacios o puntuación)
        greek_pattern = r'(?<![a-zA-Z])([αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΠΣΦΨΩ])(?![a-zA-Z])'

        combined = '|'.join(f'({p})' for p in preserve_patterns)
        combined += f'|({greek_pattern})'

        last_end = 0
        for match in re.finditer(combined, texto):
            if match.start() > last_end:
                pre = texto[last_end:match.start()]
                if pre.strip():
                    segments.append({"text": pre, "translate": True})
                elif pre:
                    segments.append({"text": pre, "translate": False})

            segments.append({"text": match.group(), "translate": False})
            last_end = match.end()

        if last_end < len(texto):
            remaining = texto[last_end:]
            if remaining.strip():
                segments.append({"text": remaining, "translate": True})
            elif remaining:
                segments.append({"text": remaining, "translate": False})

        if not segments:
            segments = [{"text": texto, "translate": True}]

        return segments