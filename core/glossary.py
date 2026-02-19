"""
Mega-glosario técnico por área de conocimiento.
Términos que deben protegerse o corregirse durante la traducción.
"""
import re


class Glossary:
    """
    Gestiona el glosario técnico multi-área.
    
    Estrategia:
    - Pre-traducción: reemplaza términos clave por placeholders
      para que la API no los traduzca mal.
    - Post-traducción: restaura los placeholders con la traducción
      correcta del glosario.
    """

    # Formato del placeholder: ⟦GLOSS_42⟧
    # Usamos caracteres Unicode raros que ningún traductor tocará
    PLACEHOLDER_PREFIX = "⟦GLOSS_"
    PLACEHOLDER_SUFFIX = "⟧"

    GLOSARIO_POR_AREA = {
        "ESTADISTICA": {
            "Unit Maxwell-Boltzmann": "Unit Maxwell-Boltzmann",
            "Birnbaum-Saunders": "Birnbaum-Saunders",
            "Weibull": "Weibull",
            "Gaussian": "Gaussiana",
            "Poisson": "Poisson",
            "Bernoulli": "Bernoulli",
            "Bayesian": "Bayesiano",
            "frequentist": "frecuentista",
            "p-value": "valor p",
            "p-values": "valores p",
            "e-value": "valor e",
            "z-score": "puntuación z",
            "t-test": "prueba t",
            "F-test": "prueba F",
            "GAMLSS": "GAMLSS",
            "ANOVA": "ANOVA",
            "ANCOVA": "ANCOVA",
            "MANOVA": "MANOVA",
            "Chi-square": "Chi-cuadrado",
            "chi-squared": "chi-cuadrado",
            "goodness-of-fit": "bondad de ajuste",
            "goodness of fit": "bondad de ajuste",
            "homoscedasticity": "homocedasticidad",
            "heteroscedasticity": "heterocedasticidad",
            "multicollinearity": "multicolinealidad",
            "autocorrelation": "autocorrelación",
            "outlier": "valor atípico",
            "outliers": "valores atípicos",
            "bootstrap": "bootstrap",
            "bootstrapping": "bootstrapping",
            "jackknife": "jackknife",
            "Monte Carlo": "Monte Carlo",
            "Markov Chain": "cadena de Markov",
            "MCMC": "MCMC",
            "R-squared": "R-cuadrado",
            "adjusted R-squared": "R-cuadrado ajustado",
            "standard deviation": "desviación estándar",
            "standard error": "error estándar",
            "confidence interval": "intervalo de confianza",
            "prediction interval": "intervalo de predicción",
            "credible interval": "intervalo creíble",
            "likelihood": "verosimilitud",
            "log-likelihood": "log-verosimilitud",
            "maximum likelihood": "máxima verosimilitud",
            "MLE": "MLE",
            "OLS": "OLS",
            "GLS": "GLS",
            "WLS": "WLS",
            "GLM": "GLM",
            "GAM": "GAM",
            "CDF": "CDF",
            "PDF": "PDF",
            "PMF": "PMF",
            "MGF": "MGF",
            "i.i.d.": "i.i.d.",
            "H0": "H₀",
            "H1": "H₁",
            "null hypothesis": "hipótesis nula",
            "alternative hypothesis": "hipótesis alternativa",
            "Type I error": "error Tipo I",
            "Type II error": "error Tipo II",
            "prior": "a priori",
            "posterior": "a posteriori",
            "Cramér-von Mises": "Cramér-von Mises",
            "Kolmogorov-Smirnov": "Kolmogorov-Smirnov",
            "Anderson-Darling": "Anderson-Darling",
            "Shapiro-Wilk": "Shapiro-Wilk",
            "Lilliefors": "Lilliefors",
            "Durbin-Watson": "Durbin-Watson",
            "Akaike": "Akaike",
            "AIC": "AIC",
            "BIC": "BIC",
            "hazard function": "función de riesgo",
            "survival function": "función de supervivencia",
            "Kaplan-Meier": "Kaplan-Meier",
            "Cox regression": "regresión de Cox",
            "random variable": "variable aleatoria",
            "sample size": "tamaño de muestra",
            "degrees of freedom": "grados de libertad",
            "bias": "sesgo",
            "unbiased": "insesgado",
            "consistent": "consistente",
            "sufficient statistic": "estadístico suficiente",
            "Fisher information": "información de Fisher",
        },
        "INDUSTRIAL": {
            "Six Sigma": "Six Sigma",
            "Lean Manufacturing": "Lean Manufacturing",
            "Lean": "Lean",
            "JIT": "JIT",
            "Just-in-Time": "Justo a Tiempo",
            "Kanban": "Kanban",
            "Poka-yoke": "Poka-yoke",
            "Kaizen": "Kaizen",
            "Gemba": "Gemba",
            "Muda": "Muda",
            "BOM": "BOM",
            "Supply Chain": "cadena de suministro",
            "KPI": "KPI",
            "R&R": "R&R",
            "FMEA": "AMFE",
            "DMAIC": "DMAIC",
            "SIPOC": "SIPOC",
            "Cpk": "Cpk",
            "control chart": "carta de control",
            "Pareto chart": "diagrama de Pareto",
            "Ishikawa": "Ishikawa",
            "fishbone diagram": "diagrama de espina de pescado",
            "root cause analysis": "análisis de causa raíz",
            "bottleneck": "cuello de botella",
            "throughput": "rendimiento",
            "lead time": "tiempo de entrega",
            "cycle time": "tiempo de ciclo",
            "takt time": "tiempo takt",
            "work in progress": "trabajo en proceso",
            "WIP": "WIP",
        },
        "SISTEMAS": {
            "Python": "Python",
            "JavaScript": "JavaScript",
            "Java": "Java",
            "C++": "C++",
            "R": "R",
            "MATLAB": "MATLAB",
            "Framework": "framework",
            "Backend": "backend",
            "Frontend": "frontend",
            "API": "API",
            "REST": "REST",
            "Machine Learning": "Machine Learning",
            "Deep Learning": "Deep Learning",
            "Neural Network": "red neuronal",
            "Convolutional Neural Network": "red neuronal convolucional",
            "CNN": "CNN",
            "RNN": "RNN",
            "LSTM": "LSTM",
            "Transformer": "Transformer",
            "Random Forest": "Random Forest",
            "Gradient Boosting": "Gradient Boosting",
            "XGBoost": "XGBoost",
            "SVM": "SVM",
            "Support Vector Machine": "máquina de vectores de soporte",
            "k-means": "k-means",
            "clustering": "clustering",
            "classification": "clasificación",
            "regression": "regresión",
            "cross-validation": "validación cruzada",
            "k-fold": "k-fold",
            "blockchain": "blockchain",
            "smart contract": "contrato inteligente",
            "bug": "bug",
            "dataset": "dataset",
            "training set": "conjunto de entrenamiento",
            "test set": "conjunto de prueba",
            "validation set": "conjunto de validación",
            "overfitting": "sobreajuste",
            "underfitting": "subajuste",
            "feature engineering": "ingeniería de características",
            "hyperparameter": "hiperparámetro",
            "epoch": "época",
            "batch size": "tamaño de lote",
            "learning rate": "tasa de aprendizaje",
            "GPU": "GPU",
            "CPU": "CPU",
            "RAM": "RAM",
        },
        "ELECTRONICA": {
            "MOSFET": "MOSFET",
            "BJT": "BJT",
            "PCB": "PCB",
            "FPGA": "FPGA",
            "ASIC": "ASIC",
            "PLC": "PLC",
            "SCADA": "SCADA",
            "AC": "AC",
            "DC": "DC",
            "PWM": "PWM",
            "ADC": "ADC",
            "DAC": "DAC",
            "VHDL": "VHDL",
            "Verilog": "Verilog",
            "Arduino": "Arduino",
            "Raspberry Pi": "Raspberry Pi",
            "IoT": "IoT",
            "embedded system": "sistema embebido",
            "firmware": "firmware",
            "microcontroller": "microcontrolador",
            "op-amp": "amplificador operacional",
            "feedback": "retroalimentación",
            "gain": "ganancia",
            "bandwidth": "ancho de banda",
            "impedance": "impedancia",
        },
        "MECANICA": {
            "CAD": "CAD",
            "CAM": "CAM",
            "CAE": "CAE",
            "CNC": "CNC",
            "FEM": "FEM",
            "FEA": "FEA",
            "CFD": "CFD",
            "torque": "torque",
            "stress": "esfuerzo",
            "strain": "deformación",
            "shear stress": "esfuerzo cortante",
            "shear": "cortante",
            "bearing": "rodamiento",
            "fatigue": "fatiga",
            "creep": "fluencia",
            "yield strength": "límite elástico",
            "tensile strength": "resistencia a la tracción",
            "Young's modulus": "módulo de Young",
            "Poisson's ratio": "relación de Poisson",
            "Reynolds number": "número de Reynolds",
            "Mach number": "número de Mach",
            "Navier-Stokes": "Navier-Stokes",
            "boundary layer": "capa límite",
            "heat transfer": "transferencia de calor",
            "convection": "convección",
            "conduction": "conducción",
            "radiation": "radiación",
        },
    }

    def __init__(self, areas_activas: list[str] = None):
        """
        Args:
            areas_activas: Lista de áreas a activar.
                          None = todas activas.
                          Ej: ["ESTADISTICA", "SISTEMAS"]
        """
        self.glosario_activo = {}
        self._placeholder_map = {}  # placeholder → traducción correcta

        if areas_activas is None:
            areas_activas = list(self.GLOSARIO_POR_AREA.keys())

        for area in areas_activas:
            if area in self.GLOSARIO_POR_AREA:
                self.glosario_activo.update(self.GLOSARIO_POR_AREA[area])

        # Ordenar por longitud descendente para evitar reemplazos parciales
        # "standard deviation" debe matchear antes que "standard"
        self._terminos_ordenados = sorted(
            self.glosario_activo.keys(),
            key=len,
            reverse=True,
        )

    def proteger_terminos(self, texto: str) -> str:
        """
        PRE-traducción: Reemplaza términos del glosario por placeholders
        para que la API de traducción no los toque.
        
        "The p-value was 0.05" → "The ⟦GLOSS_0⟧ was 0.05"
        """
        self._placeholder_map = {}
        resultado = texto

        for idx, termino in enumerate(self._terminos_ordenados):
            patron = r'\b' + re.escape(termino) + r'\b'
            placeholder = f"{self.PLACEHOLDER_PREFIX}{idx}{self.PLACEHOLDER_SUFFIX}"

            if re.search(patron, resultado, flags=re.IGNORECASE):
                self._placeholder_map[placeholder] = self.glosario_activo[termino]
                resultado = re.sub(
                    patron, placeholder, resultado, flags=re.IGNORECASE
                )

        return resultado

    def restaurar_terminos(self, texto_traducido: str) -> str:
        """
        POST-traducción: Restaura los placeholders con las traducciones
        correctas del glosario.
        
        "El ⟦GLOSS_0⟧ fue 0.05" → "El valor p fue 0.05"
        """
        resultado = texto_traducido
        for placeholder, traduccion in self._placeholder_map.items():
            resultado = resultado.replace(placeholder, traduccion)
        return resultado

    def corregir_post_traduccion(self, texto: str) -> str:
        """
        Fallback: Corrección directa post-traducción para términos
        que la API haya traducido mal a pesar de los placeholders.
        """
        resultado = texto
        for ingles, espanol in self.glosario_activo.items():
            patron = r'\b' + re.escape(ingles) + r'\b'
            resultado = re.sub(patron, espanol, resultado, flags=re.IGNORECASE)
        return resultado

    @classmethod
    def get_areas_disponibles(cls) -> list[str]:
        """Retorna las áreas de conocimiento disponibles."""
        return list(cls.GLOSARIO_POR_AREA.keys())

    @classmethod
    def get_terminos_por_area(cls, area: str) -> dict:
        """Retorna los términos de un área específica."""
        return cls.GLOSARIO_POR_AREA.get(area, {})