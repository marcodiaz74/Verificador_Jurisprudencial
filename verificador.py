# verificador.py
# Generación de enlaces de búsqueda manual para citas jurídicas colombianas.
#
# SIN dependencias externas ni imports de otros módulos del proyecto.
# Acepta cualquier objeto con atributos: tipo, subtipo, referencia, estado, fuente, enlace
# (duck typing — no requiere importar la clase Cita).

import re
from urllib.parse import quote_plus


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUCCIÓN DE URLs DE BÚSQUEDA
# ─────────────────────────────────────────────────────────────────────────────

def _google_suin(termino: str) -> str:
    q = f'site:suin-juriscol.gov.co "{termino}"'
    return f"https://www.google.com/search?q={quote_plus(q)}"


def _bing_suin(termino: str) -> str:
    q = f'site:suin-juriscol.gov.co "{termino}"'
    return f"https://www.bing.com/search?q={quote_plus(q)}"


def _google_general(termino: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(termino)}"


def _google_scholar(termino: str) -> str:
    return f"https://scholar.google.com/scholar?q={quote_plus(termino)}"


# ─────────────────────────────────────────────────────────────────────────────
# ENLACES POR TIPO
# ─────────────────────────────────────────────────────────────────────────────

def _enlaces_corte_constitucional(referencia: str) -> dict:
    m = re.match(r"([A-Z]+)[\-\u2013](\d{1,4})(?:[/\-](\d{2,4}))?", referencia.strip())
    if m:
        tipo, numero, anio_raw = m.groups()
        anio = ""
        if anio_raw:
            anio = (("20" if int(anio_raw) <= 30 else "19") + anio_raw
                    if len(str(anio_raw)) == 2 else str(anio_raw))
        identificador = f"{tipo}-{numero}"
        termino_suin = f"{identificador}/{anio}" if anio else identificador
        url_relatoria = (
            f"https://www.corteconstitucional.gov.co/relatoria/{anio}/{tipo}-{numero}.htm"
            if anio else "https://www.corteconstitucional.gov.co/relatoria/"
        )
    else:
        termino_suin = referencia
        url_relatoria = "https://www.corteconstitucional.gov.co/relatoria/"

    return {
        "suin_google":    _google_suin(termino_suin),
        "suin_bing":      _bing_suin(termino_suin),
        "relatoria_cc":   url_relatoria,
        "google_general": _google_general(
            f'Corte Constitucional Colombia sentencia "{termino_suin}"'
        ),
    }


def _enlaces_corte_suprema(referencia: str) -> dict:
    ref = referencia.strip().replace("\u2013", "-").replace("\u2014", "-")
    m = re.match(r"(SC|SL|SP)\s*(\d+)[-\u2013](\d{4})", ref, re.IGNORECASE)
    if m:
        sala, num, anio = m.groups()
        termino_suin = f"{sala}{num}-{anio}"
    else:
        m2 = re.search(r"(\d{4,})", ref)
        termino_suin = m2.group(1) if m2 else ref

    return {
        "suin_google":    _google_suin(termino_suin),
        "suin_bing":      _bing_suin(termino_suin),
        "relatoria_csj":  "https://cortesuprema.gov.co/corte/index.php/relatoria/",
        "google_general": _google_general(
            f'Corte Suprema de Justicia Colombia "{termino_suin}"'
        ),
    }


def _enlaces_consejo_estado(referencia: str) -> dict:
    ref = re.sub(
        r"(?:Exp(?:ediente)?|Rad(?:icado)?)[.\s]*", "",
        referencia, flags=re.IGNORECASE
    ).strip().replace("\u2013", "-").replace("\u2014", "-")

    termino_suin = ref
    ref_sin_guiones = re.sub(r"[-\s]", "", ref)
    termino_alt = ref_sin_guiones if ref_sin_guiones.isdigit() and ref_sin_guiones != ref else None

    enlaces = {
        "suin_google":    _google_suin(termino_suin),
        "suin_bing":      _bing_suin(termino_suin),
        "buscador_ce":    "https://www.consejodeestado.gov.co/busquedas/buscador-jurisprudencia/",
        "google_general": _google_general(
            f'Consejo de Estado Colombia "{termino_suin}"'
        ),
    }
    if termino_alt:
        enlaces["suin_num"] = _google_suin(termino_alt)
    return enlaces


def _enlaces_norma(referencia: str, subtipo: str) -> dict:
    numero = re.search(r"\d+", referencia)
    anio   = re.search(r"(?:19|20)\d{2}", referencia)
    url_fp = "https://www.funcionpublica.gov.co/eva/gestornormativo/norma_busqueda.php"
    if numero and anio:
        url_fp += f"?norma={numero.group()}&anio={anio.group()}"

    return {
        "suin_google":      _google_suin(referencia),
        "suin_bing":        _bing_suin(referencia),
        "funcion_publica":  url_fp,
        "google_general":   _google_general(
            f'"{referencia}" Colombia site:suin-juriscol.gov.co OR site:funcionpublica.gov.co'
        ),
    }


def _enlaces_doctrina(referencia: str, subtipo: str) -> dict:
    if subtipo == "ISBN":
        isbn = re.sub(r"[\s\-\u2013]", "", referencia)
        return {
            "open_library":   f"https://openlibrary.org/isbn/{isbn}",
            "google_books":   _google_general(f"ISBN {isbn}"),
            "suin_google":    _google_suin(referencia),
        }
    elif subtipo == "DOI":
        return {
            "doi_org":        f"https://doi.org/{referencia}",
            "google_scholar": _google_scholar(referencia),
        }
    else:
        return {
            "google_scholar": _google_scholar(referencia),
            "suin_google":    _google_suin(referencia),
        }


# ─────────────────────────────────────────────────────────────────────────────
# FORMATEAR PARA LA TABLA
# ─────────────────────────────────────────────────────────────────────────────

_ETIQUETAS = {
    "suin_google":    "🔍 Buscar en SUIN (Google)",
    "suin_bing":      "🔍 Buscar en SUIN (Bing)",
    "suin_num":       "🔍 Buscar en SUIN (radicado sin guiones)",
    "relatoria_cc":   "⚖️ Relatoría Corte Constitucional",
    "relatoria_csj":  "🏛️ Relatoría Corte Suprema",
    "buscador_ce":    "🏢 Buscador Consejo de Estado",
    "funcion_publica":"📋 Función Pública",
    "open_library":   "📚 Open Library",
    "google_books":   "📚 Google Books",
    "doi_org":        "📄 doi.org",
    "google_general": "🌐 Google general",
    "google_scholar": "🎓 Google Scholar",
}


def _formatear(enlaces: dict):
    """Devuelve (enlace_principal, descripcion_con_todos_los_enlaces)."""
    principal = enlaces.get("suin_google") or next(
        (v for v in enlaces.values() if v), ""
    )
    partes = []
    for clave, url in enlaces.items():
        if url:
            partes.append(f"{_ETIQUETAS.get(clave, clave)}: {url}")
    return principal, " | ".join(partes)


# ─────────────────────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────────────────────

def verificar_cita(cita, fuentes_activas=None, sesion=None):
    """
    Genera enlaces de búsqueda manual para una cita.
    Acepta cualquier objeto con atributos tipo/subtipo/referencia/estado/fuente/enlace.
    Sin peticiones HTTP. Funciona en cualquier entorno.
    """
    tipo = getattr(cita, "tipo", "")
    subtipo = getattr(cita, "subtipo", "")
    referencia = getattr(cita, "referencia", "")

    if tipo == "corte_constitucional":
        enlaces = _enlaces_corte_constitucional(referencia)
    elif tipo == "corte_suprema":
        enlaces = _enlaces_corte_suprema(referencia)
    elif tipo == "consejo_estado":
        enlaces = _enlaces_consejo_estado(referencia)
    elif tipo == "norma":
        enlaces = _enlaces_norma(referencia, subtipo)
    elif tipo == "doctrina":
        enlaces = _enlaces_doctrina(referencia, subtipo)
    else:
        enlaces = {"google_general": _google_general(referencia)}

    principal, descripcion = _formatear(enlaces)
    cita.estado = "generado"
    cita.enlace = principal
    cita.fuente = descripcion
    return cita


def verificar_todas(citas, fuentes_activas=None, callback_progreso=None):
    """Genera enlaces para todas las citas. Sin red, instantáneo."""
    total = len(citas)
    for i, cita in enumerate(citas):
        if callback_progreso:
            callback_progreso(i, total, cita)
        verificar_cita(cita)
    return citas


def _crear_sesion():
    """Stub de compatibilidad. No hace nada."""
    return None
