# verificador.py
# Verificación de citas jurídicas colombianas.
#
# ENFOQUE: generación de enlaces de búsqueda manual.
#
# Diagnóstico confirmado: los servidores cloud (Streamlit Community Cloud)
# tienen bloqueado el acceso a sitios gubernamentales colombianos y a motores
# de búsqueda. Por tanto, la verificación automática (HTTP scraping) no es
# posible desde ese entorno.
#
# Solución implementada:
#   Para cada cita se generan TRES enlaces directos y funcionales que el
#   usuario puede abrir con un clic desde su navegador:
#
#   1. SUIN-Juriscol  → búsqueda en Google con site:suin-juriscol.gov.co
#   2. Fuente oficial → URL directa de la relatoría / buscador de cada corte
#   3. Google Scholar → búsqueda académica como respaldo
#
#   El campo `estado` se marca siempre como "generado" para distinguirlo
#   de una verificación automática real. El campo `enlace` contiene el
#   enlace principal (SUIN via Google), y el campo `fuente` describe
#   todos los enlaces disponibles separados por " | ".
#
# El procesamiento es 100% local (sin peticiones HTTP), por lo que
# funciona en cualquier entorno incluyendo Streamlit Cloud.

import re
from urllib.parse import quote_plus
from extractor import Cita

# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUCCIÓN DE ENLACES
# ─────────────────────────────────────────────────────────────────────────────

def _google_suin(termino: str) -> str:
    """Google con site:suin-juriscol.gov.co — devuelve resultados directos de SUIN."""
    q = f'site:suin-juriscol.gov.co "{termino}"'
    return f"https://www.google.com/search?q={quote_plus(q)}"


def _bing_suin(termino: str) -> str:
    """Bing con site:suin-juriscol.gov.co — alternativa a Google."""
    q = f'site:suin-juriscol.gov.co "{termino}"'
    return f"https://www.bing.com/search?q={quote_plus(q)}"


def _google_general(termino: str) -> str:
    """Búsqueda general en Google sin restricción de sitio."""
    return f"https://www.google.com/search?q={quote_plus(termino)}"


def _google_scholar(termino: str) -> str:
    """Google Scholar — útil para doctrina y referencias académicas."""
    return f"https://scholar.google.com/scholar?q={quote_plus(termino)}"


# ─────────────────────────────────────────────────────────────────────────────
# ENLACES POR TIPO DE CORTE / NORMA
# ─────────────────────────────────────────────────────────────────────────────

def _enlaces_corte_constitucional(referencia: str) -> dict:
    """
    Genera enlaces para providencias de la Corte Constitucional.
    Ejemplo: T-123/2020, C-456/18, SU-789/2021, A-045/2019
    """
    # Normalizar año
    m = re.match(r"([A-Z]+)[\-–](\d{1,4})(?:[/\-](\d{2,4}))?", referencia.strip())
    tipo, numero, anio_raw = (m.groups() if m else ("", referencia, ""))
    anio = ""
    if anio_raw:
        if len(str(anio_raw)) == 2:
            anio = ("20" if int(anio_raw) <= 30 else "19") + str(anio_raw)
        else:
            anio = str(anio_raw)

    identificador = f"{tipo}-{numero}" if tipo else referencia

    # URL directa de relatoría (formato conocido de la CC)
    url_relatoria = (
        f"https://www.corteconstitucional.gov.co/relatoria/{anio}/{tipo}-{numero}.htm"
        if anio else
        f"https://www.corteconstitucional.gov.co/relatoria/"
    )

    # Término de búsqueda para SUIN
    termino_suin   = f"{identificador}/{anio}" if anio else identificador
    termino_google = f'Corte Constitucional Colombia sentencia "{identificador}" {anio}'.strip()

    return {
        "suin_google":    _google_suin(termino_suin),
        "suin_bing":      _bing_suin(termino_suin),
        "relatoria_cc":   url_relatoria,
        "google_general": _google_general(termino_google),
    }


def _enlaces_corte_suprema(referencia: str) -> dict:
    """
    Genera enlaces para sentencias de la Corte Suprema de Justicia.
    Ejemplo: SC1234-2021, SL5678-2019, SP9012-2020, Rad. 45678
    """
    ref = referencia.strip().replace("–", "-").replace("—", "-")

    # Extraer sala y número
    m = re.match(r"(SC|SL|SP)\s*(\d+)[-–](\d{4})", ref, re.IGNORECASE)
    if m:
        sala, num, anio = m.groups()
        termino_suin   = f"{sala}{num}-{anio}"
        termino_google = f'Corte Suprema de Justicia Colombia "{sala}{num}-{anio}"'
    else:
        m2 = re.search(r"(\d{4,})", ref)
        num = m2.group(1) if m2 else ref
        termino_suin   = num
        termino_google = f'Corte Suprema de Justicia Colombia "{ref}"'

    return {
        "suin_google":    _google_suin(termino_suin),
        "suin_bing":      _bing_suin(termino_suin),
        "relatoria_csj":  "https://cortesuprema.gov.co/corte/index.php/relatoria/",
        "google_general": _google_general(termino_google),
    }


def _enlaces_consejo_estado(referencia: str) -> dict:
    """
    Genera enlaces para providencias del Consejo de Estado.
    Ejemplo: 11001-03-24-000-2019-00319-00, Exp. 47685
    """
    ref = re.sub(
        r"(?:Exp(?:ediente)?|Rad(?:icado)?)[.\s]*", "",
        referencia, flags=re.IGNORECASE
    ).strip()

    # Versión con guiones (como aparece en los documentos)
    ref_guiones = ref.replace("–", "-").replace("—", "-")

    # Versión sin guiones (como la indexa SUIN)
    ref_sin_guiones = re.sub(r"[-–\s]", "", ref_guiones)
    if not ref_sin_guiones.isdigit():
        ref_sin_guiones = ref_guiones

    termino_suin   = ref_guiones
    termino_google = f'Consejo de Estado Colombia "{ref_guiones}"'

    return {
        "suin_google":    _google_suin(termino_suin),
        "suin_bing":      _bing_suin(termino_suin),
        "suin_num":       _google_suin(ref_sin_guiones) if ref_sin_guiones != ref_guiones else None,
        "buscador_ce":    "https://www.consejodeestado.gov.co/busquedas/buscador-jurisprudencia/",
        "google_general": _google_general(termino_google),
    }


def _enlaces_norma(referencia: str, subtipo: str) -> dict:
    """
    Genera enlaces para normas legales.
    Ejemplo: Ley 1581 de 2012, Decreto 1377 de 2013
    """
    termino_suin   = referencia
    termino_google = f'"{referencia}" Colombia site:suin-juriscol.gov.co OR site:funcionpublica.gov.co'

    # Extraer número y año para el gestor de Función Pública
    numero = re.search(r"\d+", referencia)
    anio   = re.search(r"(?:19|20)\d{2}", referencia)
    url_fp = "https://www.funcionpublica.gov.co/eva/gestornormativo/norma_busqueda.php"
    if numero and anio:
        url_fp += f"?norma={numero.group()}&anio={anio.group()}"

    return {
        "suin_google":      _google_suin(termino_suin),
        "suin_bing":        _bing_suin(termino_suin),
        "funcion_publica":  url_fp,
        "google_general":   _google_general(termino_google),
    }


def _enlaces_doctrina(referencia: str, subtipo: str) -> dict:
    """Genera enlaces para doctrina (ISBN, DOI, revistas)."""
    if subtipo == "ISBN":
        isbn = re.sub(r"[\s\-–]", "", referencia)
        return {
            "open_library": f"https://openlibrary.org/isbn/{isbn}",
            "google_books": f"https://www.google.com/search?q={quote_plus('ISBN ' + isbn)}",
            "suin_google":  _google_suin(referencia),
        }
    elif subtipo == "DOI":
        return {
            "doi_org":      f"https://doi.org/{referencia}",
            "google_scholar": _google_scholar(referencia),
        }
    else:
        return {
            "google_scholar": _google_scholar(referencia),
            "suin_google":    _google_suin(referencia),
        }


# ─────────────────────────────────────────────────────────────────────────────
# FORMATEAR FUENTE Y ENLACE PRINCIPAL PARA LA TABLA
# ─────────────────────────────────────────────────────────────────────────────

_ETIQUETAS = {
    # corte_constitucional
    "suin_google":    "🔍 Buscar en SUIN (Google)",
    "suin_bing":      "🔍 Buscar en SUIN (Bing)",
    "suin_num":       "🔍 Buscar en SUIN (radicado)",
    "relatoria_cc":   "⚖️ Relatoría CC",
    "relatoria_csj":  "🏛️ Relatoría CSJ",
    "buscador_ce":    "🏢 Buscador CE",
    "funcion_publica":"📋 Función Pública",
    "open_library":   "📚 Open Library",
    "google_books":   "📚 Google Books",
    "doi_org":        "📄 doi.org",
    "google_general": "🌐 Buscar en Google",
    "google_scholar": "🎓 Google Scholar",
}


def _formatear(enlaces: dict) -> tuple[str, str]:
    """
    Devuelve (enlace_principal, descripcion_fuentes).

    enlace_principal → URL del primer enlace SUIN disponible (para la columna Enlace).
    descripcion_fuentes → texto con todos los enlaces, separados por " | ".
    """
    # Enlace principal: siempre el de SUIN via Google
    principal = enlaces.get("suin_google") or next(iter(enlaces.values()))

    # Descripción con todos los enlaces no nulos
    partes = []
    for clave, url in enlaces.items():
        if url:
            etiqueta = _ETIQUETAS.get(clave, clave)
            partes.append(f"{etiqueta}: {url}")

    descripcion = " | ".join(partes)
    return principal, descripcion


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PÚBLICA: verificar_cita
# ─────────────────────────────────────────────────────────────────────────────

def verificar_cita(cita: Cita, fuentes_activas: dict = None, sesion=None) -> Cita:
    """
    Genera los enlaces de búsqueda manual para una cita.

    No realiza peticiones HTTP. Todos los enlaces son URLs funcionales
    que el usuario puede abrir directamente en su navegador.

    Estado resultante: "generado" (distingue de verificación automática).
    """
    if cita.tipo == "corte_constitucional":
        enlaces = _enlaces_corte_constitucional(cita.referencia)

    elif cita.tipo == "corte_suprema":
        enlaces = _enlaces_corte_suprema(cita.referencia)

    elif cita.tipo == "consejo_estado":
        enlaces = _enlaces_consejo_estado(cita.referencia)

    elif cita.tipo == "norma":
        enlaces = _enlaces_norma(cita.referencia, cita.subtipo)

    elif cita.tipo == "doctrina":
        enlaces = _enlaces_doctrina(cita.referencia, cita.subtipo)

    else:
        enlaces = {"google_general": _google_general(cita.referencia)}

    enlace_principal, descripcion_fuentes = _formatear(enlaces)

    cita.estado = "generado"
    cita.enlace = enlace_principal
    cita.fuente = descripcion_fuentes

    return cita


def verificar_todas(
    citas: list,
    fuentes_activas: dict = None,
    callback_progreso=None,
) -> list:
    """
    Genera enlaces de búsqueda para todas las citas.
    Proceso instantáneo — sin peticiones HTTP.
    """
    total = len(citas)
    for i, cita in enumerate(citas):
        if callback_progreso:
            callback_progreso(i, total, cita)
        verificar_cita(cita, fuentes_activas)
    return citas


# ─────────────────────────────────────────────────────────────────────────────
# Compatibilidad: _crear_sesion (requerida por app.py)
# ─────────────────────────────────────────────────────────────────────────────

def _crear_sesion():
    """Stub de compatibilidad — no se usa ninguna sesión HTTP."""
    return None
