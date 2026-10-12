"""Filtro anti-toxicidad (procesamiento de lenguaje natural con NLTK).

Clasifica cada mensaje como:
    NONE   = limpio
    MILD   = ofensivo leve (burlas, "noob", "basura")
    SEVERE = insulto fuerte o groserías

Pasos (PNL):
  1. Normalización: minúsculas, sin tildes, "leetspeak" (1d10ta -> idiota) y letras
     repetidas (idiotaaaa -> idiota).
  2. Tokenización con NLTK (wordpunct_tokenize).
  3. Stemming con NLTK (SnowballStemmer en español e inglés): reduce cada palabra a su raíz,
     así "idiotas", "inútiles" o "desinstale" se detectan con una sola entrada en la lista.
  4. Búsqueda de la raíz en las listas de palabras y de frases.

No hace falta descargar datos de NLTK: el tokenizador y el stemmer funcionan sin internet.
"""

import re
import unicodedata
from functools import lru_cache
from typing import Literal

from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import wordpunct_tokenize

Nivel = Literal["NONE", "MILD", "SEVERE"]
NivelFiltro = Literal["OFF", "MEDIUM", "STRICT"]

# Palabras base; las variantes (plural, femenino, verbos) se cubren con el stemming
PALABRAS = {
    "SEVERE": [
        # Español
        "idiota", "imbecil", "estupido", "inutil", "pendejo", "cabron", "mierda", "puta", "puto",
        "carajo", "joder", "gilipollas", "subnormal", "retrasado", "maldito", "hijueputa", "malparido",
        "mamaguevo", "pendeja", "huevon", "culero", "zorra", "hdp", "ctm",
        # Inglés
        "idiot", "stupid", "moron", "retard", "fuck", "fucking", "shit", "bitch", "bastard", "asshole",
        "dumbass", "cunt", "dickhead",
    ],
    "MILD": [
        # Español
        "noob", "manco", "basura", "malisimo", "pesimo", "tonto", "tonta", "bobo", "payaso", "perdedor",
        "inservible", "desinstala", "lloron", "patetico", "chafa",
        # Inglés
        "trash", "garbage", "loser", "sucks", "dumb", "pathetic", "clown", "uninstall", "crybaby",
    ],
}

# Frases que solo son tóxicas juntas (se buscan en el texto normalizado)
FRASES = {
    "SEVERE": ["kill yourself", "kys", "matate", "muerete", "ojala te mueras"],
    "MILD": ["vete a jugar otra cosa", "go back to bronze", "get good", "ez noob"],
}

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
_STEMMERS = (SnowballStemmer("spanish"), SnowballStemmer("english"))


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))  # quita tildes
    texto = texto.translate(_LEET)
    return re.sub(r"(\w)\1+", r"\1", texto)  # "idiotaaa" -> "idiota" (se aplica igual a las listas)


def _raices(palabra: str) -> set[str]:
    return {palabra} | {stemmer.stem(palabra) for stemmer in _STEMMERS}


@lru_cache
def _diccionario() -> dict[str, Nivel]:
    """raíz -> nivel. Se calcula una sola vez."""
    raices: dict[str, Nivel] = {}
    for nivel in ("MILD", "SEVERE"):  # SEVERE va después: si una raíz está en las dos listas, gana
        for palabra in PALABRAS[nivel]:
            for raiz in _raices(normalizar(palabra)):
                # Raíces muy cortas darían falsos positivos (por ejemplo "mal")
                if len(raiz) >= 3:
                    raices[raiz] = nivel
    return raices


def clasificar(texto: str) -> Nivel:
    normal = normalizar(texto)
    nivel: Nivel = "NONE"

    con_espacios = f" {' '.join(re.findall(r'[a-z]+', normal))} "
    for posible in ("SEVERE", "MILD"):
        if any(f" {normalizar(frase)} " in con_espacios for frase in FRASES[posible]):
            if posible == "SEVERE":
                return "SEVERE"
            nivel = "MILD"

    diccionario = _diccionario()
    for token in wordpunct_tokenize(normal):
        if not token.isalpha():
            continue
        for raiz in _raices(token):
            encontrado = diccionario.get(raiz)
            if encontrado == "SEVERE":
                return "SEVERE"
            if encontrado == "MILD":
                nivel = "MILD"
    return nivel


def se_oculta(toxicidad: Nivel, filtro: NivelFiltro) -> bool:
    """Cada jugador elige su filtro: STRICT oculta MILD y SEVERE; MEDIUM oculta SEVERE; OFF muestra todo."""
    if filtro == "STRICT":
        return toxicidad != "NONE"
    if filtro == "MEDIUM":
        return toxicidad == "SEVERE"
    return False
