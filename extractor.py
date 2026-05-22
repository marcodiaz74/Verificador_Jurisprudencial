# extractor.py
# Extracción de citas normativas y jurisprudenciales colombianas
# mediante expresiones regulares.

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Cita:
    tipo: str           # "norma" | "corte_constitucional" | "corte_suprema" | "consejo_estado" | "doctrina"
    subtipo: str        # Ley, Decreto, T-, C-, etc.
    texto_original: str # Texto tal como aparece en el documento
    referencia: str     # Referencia normalizada para búsqueda
    pagina: Optional[int] = None
    estado: str = "pendiente"   # pendiente | encontrada | no_encontrada | no_verificable
    fuente: str = ""
    enlace: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# PATRONES DE NORMAS LEGALES
# ──────────────────────────────────────────────────────────────────────────────

PATRONES_NORMAS = [
    (
        "Ley",
        re.compile(
            r"\bLey\s+(?:N[°o.]?\s*)?(\d{1,5})\s+de\s+((?:19|20)\d{2})\b",
            re.IGNORECASE
        ),
    ),
    (
        "Decreto",
        re.compile(
            r"\bDecreto(?:\s+Legislativo|\s+Ley|\s+Reglamentario|\s+Extraordinario)?\s+(?:N[°o.]?\s*)?(\d{1,5})\s+de\s+((?:19|20)\d{2})\b",
            re.IGNORECASE
        ),
    ),
    (
        "Resolución",
        re.compile(
            r"\bResolución\s+(?:N[°o.]?\s*)?(\d{1,6})\s+de\s+((?:19|20)\d{2})\b",
            re.IGNORECASE
        ),
    ),
    (
        "Acto Legislativo",
        re.compile(
            r"\bActo\s+Legislativo\s+(?:N[°o.]?\s*)?(\d{1,2})\s+de\s+((?:19|20)\d{2})\b",
            re.IGNORECASE
        ),
    ),
    (
        "Circular",
        re.compile(
            r"\bCircular\s+(?:Externa\s+|Interna\s+|Conjunta\s+)?(?:N[°o.]?\s*)?(\d{1,4})\s+(?:de\s+((?:19|20)\d{2}))?\b",
            re.IGNORECASE
        ),
    ),
    (
        "Ordenanza",
        re.compile(
            r"\bOrdenanza\s+(?:N[°o.]?\s*)?(\d{1,4})\s+de\s+((?:19|20)\d{2})\b",
            re.IGNORECASE
        ),
    ),
    (
        "Acuerdo",
        re.compile(
            r"\bAcuerdo\s+(?:Municipal\s+|Distrital\s+)?(?:N[°o.]?\s*)?(\d{1,4})\s+de\s+((?:19|20)\d{2})\b",
            re.IGNORECASE
        ),
    ),
    (
        "Código",
        re.compile(
            r"\bCódigo\s+(Civil|Penal|de\s+Comercio|Contencioso\s+Administrativo|General\s+del\s+Proceso|Sustantivo\s+del\s+Trabajo|de\s+Procedimiento\s+Penal|de\s+Infancia\s+y\s+Adolescencia|Disciplinario|Electoral)\b",
            re.IGNORECASE
        ),
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# PATRONES DE JURISPRUDENCIA — CORTE CONSTITUCIONAL
# ──────────────────────────────────────────────────────────────────────────────

PATRONES_CORTE_CONSTITUCIONAL = [
    (
        "Sentencia T",
        re.compile(r"\bT[-‐–](\d{1,4})[/\-](\d{2,4})\b"),
    ),
    (
        "Sentencia C",
        re.compile(r"\bC[-‐–](\d{1,4})[/\-](\d{2,4})\b"),
    ),
    (
        "Sentencia SU",
        re.compile(r"\bSU[-‐–](\d{1,4})[/\-](\d{2,4})\b"),
    ),
    (
        "Auto A",
        re.compile(r"\bA[-‐–](\d{1,4})[/\-](\d{2,4})\b"),
    ),
    (
        "Sentencia D",
        re.compile(r"\bD[-‐–](\d{1,4})[/\-](\d{2,4})\b"),
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# PATRONES DE JURISPRUDENCIA — CORTE SUPREMA DE JUSTICIA
# ──────────────────────────────────────────────────────────────────────────────

PATRONES_CORTE_SUPREMA = [
    (
        "Sala Civil",
        re.compile(r"\bSC\s*(\d{4,6})[-‐–](\d{4})\b"),
    ),
    (
        "Sala Laboral",
        re.compile(r"\bSL\s*(\d{4,6})[-‐–](\d{4})\b"),
    ),
    (
        "Sala Penal",
        re.compile(r"\bSP\s*(\d{4,6})[-‐–](\d{4})\b"),
    ),
    (
        "Radicado CSJ",
        re.compile(
            r"\b(?:Rad(?:icado)?\.?\s*(?:N[°o.]?\s*)?)(\d{5,})\b(?=.*(?:Corte\s+Suprema|CSJ))",
        ),
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# PATRONES DE JURISPRUDENCIA — CONSEJO DE ESTADO
# ──────────────────────────────────────────────────────────────────────────────

PATRONES_CONSEJO_ESTADO = [
    (
        "Radicado CE",
        re.compile(
            r"\b(\d{2}001[-‐–]23[-‐–]\d{2}[-‐–]000[-‐–]\d{4}[-‐–]\d{5,6}[-‐–]\d{2})\b"
        ),
    ),
    (
        "Expediente CE",
        re.compile(
            r"\b(?:Exp(?:ediente)?\.?\s*(?:N[°o.]?\s*)?)(\d{5,})\b(?=.*(?:Consejo\s+de\s+Estado|CE))"
        ),
    ),
    (
        "Sección CE",
        re.compile(
            r"\b(Secci[oó]n\s+(?:Primera|Segunda|Tercera|Cuarta|Quinta)|Sala\s+Plena\s+(?:de\s+lo\s+Contencioso\s+Administrativo)?)\b",
            re.IGNORECASE
        ),
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# PATRONES DE DOCTRINA
# ──────────────────────────────────────────────────────────────────────────────

PATRONES_DOCTRINA = [
    (
        "ISBN",
        re.compile(
            r"\bISBN(?:\s*[-‐–:]?\s*)((?:97[89][-‐–\s]?)?\d{1,5}[-‐–\s]\d{1,7}[-‐–\s]\d{1,7}[-‐–\s][\dX])\b",
            re.IGNORECASE
        ),
    ),
    (
        "DOI",
        re.compile(
            r"\b(?:https?://doi\.org/|doi:\s*)(10\.\d{4,9}/[^\s\"'<>]{1,100})\b",
            re.IGNORECASE
        ),
    ),
    (
        "Revista jurídica",
        re.compile(
            r"\bRevista\s+(?:de\s+)?(?:Derecho|Jurídica|Judicial|Penal|Civil|Constitucional|Administrativa)\s+(?:de\s+)?[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{2,40},?\s*(?:Vol(?:umen)?\.?\s*\d+)?\s*(?:N[°o.]?\s*\d+)?\s*(?:\((?:19|20)\d{2}\))?\b",
            re.IGNORECASE
        ),
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL DE EXTRACCIÓN
# ──────────────────────────────────────────────────────────────────────────────

def extraer_citas(texto: str) -> list[Cita]:
    """
    Extrae todas las citas normativas y jurisprudenciales del texto.
    Retorna una lista de objetos Cita ordenada por tipo.
    """
    citas: list[Cita] = []
    encontradas: set[str] = set()  # evitar duplicados exactos

    # --- Normas ---
    for subtipo, patron in PATRONES_NORMAS:
        for match in patron.finditer(texto):
            texto_original = match.group(0).strip()
            # Normalizar referencia
            grupos = match.groups()
            if subtipo == "Código":
                referencia = f"Código {grupos[0].strip()}"
            elif len(grupos) >= 2 and grupos[1]:
                referencia = f"{subtipo} {grupos[0].strip()} de {grupos[1].strip()}"
            else:
                referencia = f"{subtipo} {grupos[0].strip()}"

            clave = f"norma|{referencia.lower()}"
            if clave not in encontradas:
                encontradas.add(clave)
                citas.append(Cita(
                    tipo="norma",
                    subtipo=subtipo,
                    texto_original=texto_original,
                    referencia=referencia,
                ))

    # --- Corte Constitucional ---
    for subtipo, patron in PATRONES_CORTE_CONSTITUCIONAL:
        for match in patron.finditer(texto):
            texto_original = match.group(0).strip()
            grupos = match.groups()
            año = grupos[1] if len(grupos) > 1 else ""
            if len(año) == 2:
                año = ("19" if int(año) > 50 else "20") + año
            prefijo = subtipo.split()[-1]  # T, C, SU, A, D
            referencia = f"{prefijo}-{grupos[0]}/{año}"

            clave = f"cc|{referencia.lower()}"
            if clave not in encontradas:
                encontradas.add(clave)
                citas.append(Cita(
                    tipo="corte_constitucional",
                    subtipo=subtipo,
                    texto_original=texto_original,
                    referencia=referencia,
                ))

    # --- Corte Suprema de Justicia ---
    for subtipo, patron in PATRONES_CORTE_SUPREMA:
        for match in patron.finditer(texto):
            texto_original = match.group(0).strip()
            grupos = match.groups()
            if grupos:
                referencia = f"{texto_original.split()[0]}{grupos[0]}-{grupos[1]}" if len(grupos) >= 2 else f"Rad. {grupos[0]}"
            else:
                referencia = texto_original

            clave = f"csj|{referencia.lower()}"
            if clave not in encontradas:
                encontradas.add(clave)
                citas.append(Cita(
                    tipo="corte_suprema",
                    subtipo=subtipo,
                    texto_original=texto_original,
                    referencia=referencia,
                ))

    # --- Consejo de Estado ---
    for subtipo, patron in PATRONES_CONSEJO_ESTADO:
        for match in patron.finditer(texto):
            texto_original = match.group(0).strip()
            grupos = match.groups()
            referencia = grupos[0].strip() if grupos else texto_original

            clave = f"ce|{referencia.lower()}"
            if clave not in encontradas:
                encontradas.add(clave)
                citas.append(Cita(
                    tipo="consejo_estado",
                    subtipo=subtipo,
                    texto_original=texto_original,
                    referencia=referencia,
                ))

    # --- Doctrina ---
    for subtipo, patron in PATRONES_DOCTRINA:
        for match in patron.finditer(texto):
            texto_original = match.group(0).strip()
            grupos = match.groups()
            referencia = grupos[0].strip() if grupos else texto_original

            clave = f"doc|{referencia.lower()}"
            if clave not in encontradas:
                encontradas.add(clave)
                citas.append(Cita(
                    tipo="doctrina",
                    subtipo=subtipo,
                    texto_original=texto_original,
                    referencia=referencia,
                ))

    return citas


def agrupar_por_tipo(citas: list[Cita]) -> dict[str, list[Cita]]:
    """Agrupa las citas por tipo para facilitar su presentación."""
    grupos: dict[str, list[Cita]] = {
        "norma": [],
        "corte_constitucional": [],
        "corte_suprema": [],
        "consejo_estado": [],
        "doctrina": [],
    }
    for cita in citas:
        if cita.tipo in grupos:
            grupos[cita.tipo].append(cita)
    return grupos


ETIQUETAS_TIPO = {
    "norma": "📜 Normas",
    "corte_constitucional": "⚖️ Corte Constitucional",
    "corte_suprema": "🏛️ Corte Suprema de Justicia",
    "consejo_estado": "🏢 Consejo de Estado",
    "doctrina": "📚 Doctrina",
}
