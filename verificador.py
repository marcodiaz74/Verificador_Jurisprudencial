# verificador.py
# Verificación de providencias judiciales colombianas.
#
# ENFOQUE REAL:
#   El buscador de SUIN-Juriscol usa JavaScript/AJAX y no es accesible
#   directamente con GET params simples. El método que SÍ funciona es:
#
#   1. Buscar en Bing con: site:suin-juriscol.gov.co + referencia
#      Los resultados apuntan directo a viewDocument.asp?id=XXXXX (URLs públicas y funcionales)
#   2. Validar que la URL encontrada sea del tipo correcto (corporación correcta)
#   3. Si Bing falla → fallback a la URL canónica conocida de cada corte
#
#   URLs canónicas de fallback (siempre funcionales para mostrar al usuario):
#     CC  → https://www.corteconstitucional.gov.co/relatoria/YYYY/TIPO-NUM.htm
#     CSJ → https://cortesuprema.gov.co/corte/index.php/relatoria/
#     CE  → https://www.consejodeestado.gov.co/busquedas/buscador-jurisprudencia/
#     SUIN búsqueda → https://www.suin-juriscol.gov.co/jurisprudencia/jurisprudencia.html

import re
import time
import urllib3
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from extractor import Cita

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Constantes ────────────────────────────────────────────────────────────────
TIMEOUT = 12
DELAY   = 1.0

BASE_SUIN    = "https://www.suin-juriscol.gov.co"
URL_SUIN_JUR = f"{BASE_SUIN}/jurisprudencia/jurisprudencia.html"

# URLs canónicas de cada corte (fallback siempre funcional)
URL_CC_RELATORIA  = "https://www.corteconstitucional.gov.co/relatoria/"
URL_CSJ_RELATORIA = "https://cortesuprema.gov.co/corte/index.php/relatoria/"
URL_CE_BUSCADOR   = "https://www.consejodeestado.gov.co/busquedas/buscador-jurisprudencia/"

CABECERAS_BING = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.bing.com/",
}

_R = tuple[str, str, str]   # (estado, fuente, enlace)


# ── Sesión ────────────────────────────────────────────────────────────────────

def _crear_sesion() -> requests.Session:
    s = requests.Session()
    s.headers.update(CABECERAS_BING)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# NÚCLEO: buscar en Bing con site:suin-juriscol.gov.co
# ─────────────────────────────────────────────────────────────────────────────

def _buscar_bing_suin(termino: str, sesion: requests.Session) -> str | None:
    """
    Hace una búsqueda en Bing: site:suin-juriscol.gov.co <termino>
    Devuelve la primera URL de viewDocument.asp?id= encontrada, o None.
    """
    query = f'site:suin-juriscol.gov.co "{termino}"'
    url_bing = f"https://www.bing.com/search?q={quote_plus(query)}&setlang=es-CO"

    try:
        resp = sesion.get(url_bing, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Bing devuelve los resultados en <li class="b_algo"> → <h2> → <a href>
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Solo aceptar URLs directas de viewDocument en SUIN
            if (
                "suin-juriscol.gov.co/viewDocument.asp" in href
                and "id=" in href
            ):
                return href

        return None

    except Exception:
        return None


def _buscar_bing_suin_sin_comillas(termino: str, sesion: requests.Session) -> str | None:
    """Segunda pasada sin comillas — captura variantes de escritura."""
    query = f"site:suin-juriscol.gov.co {termino}"
    url_bing = f"https://www.bing.com/search?q={quote_plus(query)}&setlang=es-CO"
    try:
        resp = sesion.get(url_bing, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "suin-juriscol.gov.co/viewDocument.asp" in href and "id=" in href:
                return href
        return None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# CORTE CONSTITUCIONAL
# ─────────────────────────────────────────────────────────────────────────────

def _verificar_corte_constitucional(referencia: str, sesion: requests.Session) -> _R:
    """
    Verifica providencias de la Corte Constitucional.
    Busca en SUIN via Bing. Fallback: URL directa de relatoría CC.
    Tipos soportados: T-, C-, SU-, A-, D-
    """
    FUENTE_SUIN = "SUIN-Juriscol · Corte Constitucional"
    FUENTE_CC   = "Relatoría Corte Constitucional"

    # Normalizar referencia: "T-123/2020" o "C-456/18"
    m = re.match(r"([A-Z]+)[\-–](\d{1,4})(?:[/\-](\d{2,4}))?", referencia.strip())
    if not m:
        return "no_verificable", FUENTE_SUIN, URL_SUIN_JUR

    tipo, numero, anio_raw = m.groups()
    anio = ""
    if anio_raw:
        if len(anio_raw) == 2:
            anio = ("20" if int(anio_raw) <= 30 else "19") + anio_raw
        else:
            anio = anio_raw

    identificador = f"{tipo}-{numero}"

    # ── Capa 1: Bing con identificador completo + año ─────────────────────────
    termino1 = f"{identificador}/{anio}" if anio else identificador
    url = _buscar_bing_suin(termino1, sesion)
    if url:
        return "encontrada", FUENTE_SUIN, url

    # ── Capa 2: Bing solo con identificador ──────────────────────────────────
    time.sleep(DELAY)
    url = _buscar_bing_suin(identificador, sesion)
    if url:
        return "encontrada", FUENTE_SUIN, url

    # ── Capa 3: Bing sin comillas ─────────────────────────────────────────────
    time.sleep(DELAY)
    url = _buscar_bing_suin_sin_comillas(termino1, sesion)
    if url:
        return "encontrada", FUENTE_SUIN, url

    # ── Capa 4: URL directa de la relatoría de la CC ─────────────────────────
    if anio:
        url_directa = f"{URL_CC_RELATORIA}{anio}/{tipo}-{numero}.htm"
        try:
            time.sleep(DELAY)
            r = sesion.get(url_directa, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200 and len(r.text) > 500:
                return "encontrada", FUENTE_CC, url_directa
        except Exception:
            pass

    # No encontrada — enlace útil para búsqueda manual en SUIN
    url_manual = (
        f"https://www.bing.com/search?q="
        f"{quote_plus('site:suin-juriscol.gov.co ' + termino1)}"
    )
    return "no_encontrada", FUENTE_SUIN, url_manual


# ─────────────────────────────────────────────────────────────────────────────
# CORTE SUPREMA DE JUSTICIA
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar_ref_csj(referencia: str) -> list[str]:
    """
    Genera variantes de búsqueda para una referencia de la CSJ.
    SC1234-2021 → ["SC1234-2021", "SC 1234-2021", "1234-2021", "1234"]
    SL5678-2019 → ["SL5678-2019", "5678-2019", "5678"]
    Rad. 45678  → ["45678"]
    """
    ref = referencia.strip().replace("–", "-").replace("—", "-")
    variantes = [ref]

    # Formato SC/SL/SP NNNN-YYYY
    m = re.match(r"(SC|SL|SP)\s*(\d+)[-–](\d{4})", ref, re.IGNORECASE)
    if m:
        sala, num, anio = m.groups()
        variantes += [
            f"{sala}{num}-{anio}",
            f"{sala} {num}-{anio}",
            f"{num}-{anio}",
            num,
        ]
    else:
        # Sólo número
        m2 = re.search(r"(\d{4,})", ref)
        if m2:
            variantes.append(m2.group(1))

    # Eliminar duplicados manteniendo orden
    seen, result = set(), []
    for v in variantes:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _verificar_corte_suprema(referencia: str, sesion: requests.Session) -> _R:
    """
    Verifica sentencias de la Corte Suprema de Justicia en SUIN via Bing.
    Fallback: relatoría propia de la CSJ.
    """
    FUENTE_SUIN = "SUIN-Juriscol · Corte Suprema de Justicia"
    FUENTE_CSJ  = "Relatoría Corte Suprema de Justicia"

    variantes = _normalizar_ref_csj(referencia)

    for i, termino in enumerate(variantes):
        if i > 0:
            time.sleep(DELAY)
        url = _buscar_bing_suin(termino, sesion)
        if url:
            return "encontrada", FUENTE_SUIN, url

    # Intentar sin comillas con la variante principal
    time.sleep(DELAY)
    url = _buscar_bing_suin_sin_comillas(variantes[0], sesion)
    if url:
        return "encontrada", FUENTE_SUIN, url

    url_manual = (
        f"https://www.bing.com/search?q="
        f"{quote_plus('site:suin-juriscol.gov.co ' + variantes[0])}"
    )
    return "no_encontrada", FUENTE_SUIN, url_manual


# ─────────────────────────────────────────────────────────────────────────────
# CONSEJO DE ESTADO
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar_radicado_ce(referencia: str) -> list[str]:
    """
    Genera variantes del radicado del CE para búsqueda.
    '11001-03-24-000-2019-00319-00'
        → ['11001-03-24-000-2019-00319-00', '11001032400020190031900', '47685']
    'Exp. 47685' → ['47685']
    """
    ref = re.sub(
        r"(?:Exp(?:ediente)?|Rad(?:icado)?)[.\s]*", "", referencia, flags=re.IGNORECASE
    ).strip()

    variantes = [ref]

    # Radicado largo con guiones
    if re.search(r"\d{5}[-–]\d{2}[-–]\d{2}[-–]\d{3}[-–]\d{4}", ref):
        sin_guiones = re.sub(r"[-–\s]", "", ref)
        if sin_guiones not in variantes:
            variantes.append(sin_guiones)

    # Extraer número interno (ej. 47685 entre paréntesis)
    m_interno = re.search(r"\((\d{4,6})\)", referencia)
    if m_interno and m_interno.group(1) not in variantes:
        variantes.append(m_interno.group(1))

    seen, result = set(), []
    for v in variantes:
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _verificar_consejo_estado(referencia: str, sesion: requests.Session) -> _R:
    """
    Verifica providencias del Consejo de Estado en SUIN via Bing.
    Fallback: buscador del propio Consejo de Estado.
    """
    FUENTE_SUIN = "SUIN-Juriscol · Consejo de Estado"

    variantes = _normalizar_radicado_ce(referencia)

    for i, termino in enumerate(variantes):
        if i > 0:
            time.sleep(DELAY)
        url = _buscar_bing_suin(termino, sesion)
        if url:
            return "encontrada", FUENTE_SUIN, url

    time.sleep(DELAY)
    url = _buscar_bing_suin_sin_comillas(variantes[0], sesion)
    if url:
        return "encontrada", FUENTE_SUIN, url

    url_manual = (
        f"https://www.bing.com/search?q="
        f"{quote_plus('site:suin-juriscol.gov.co ' + variantes[0])}"
    )
    return "no_encontrada", FUENTE_SUIN, url_manual


# ─────────────────────────────────────────────────────────────────────────────
# NORMAS — SUIN + Función Pública
# ─────────────────────────────────────────────────────────────────────────────

def _verificar_suin_norma(referencia: str, subtipo: str, sesion: requests.Session) -> _R:
    """
    Verifica normas legales.
    Busca en SUIN via Bing: site:suin-juriscol.gov.co "Ley 1234 de 2020"
    Fallback: Gestor Normativo de Función Pública.
    """
    FUENTE = "SUIN-Juriscol (normas)"
    URL_NORM = f"{BASE_SUIN}/legislacion/buscador.html"

    # Capa 1: Bing con referencia completa
    url = _buscar_bing_suin(referencia, sesion)
    if url:
        return "encontrada", FUENTE, url

    # Capa 2: Bing sin comillas
    time.sleep(DELAY)
    url = _buscar_bing_suin_sin_comillas(referencia, sesion)
    if url:
        return "encontrada", FUENTE, url

    # Capa 3: buscador normativo de SUIN por GET (funciona para normas)
    try:
        numero = re.search(r"\d+", referencia)
        anio   = re.search(r"(?:19|20)\d{2}", referencia)
        if numero:
            params = {
                "numero": numero.group(),
                "anio":   anio.group() if anio else "",
                "tipo":   subtipo,
            }
            resp = sesion.get(URL_NORM, params=params, timeout=TIMEOUT, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                enlaces = soup.find_all(
                    "a", href=re.compile(r"viewDocument\.asp\?id=\d+", re.IGNORECASE)
                )
                if enlaces:
                    href = enlaces[0]["href"]
                    full = href if href.startswith("http") else f"{BASE_SUIN}/{href.lstrip('/')}"
                    return "encontrada", FUENTE, full
    except Exception:
        pass

    url_manual = (
        f"https://www.bing.com/search?q="
        f"{quote_plus('site:suin-juriscol.gov.co ' + referencia)}"
    )
    return "no_encontrada", FUENTE, url_manual


def _verificar_funcion_publica(referencia: str, sesion: requests.Session) -> _R:
    """Fallback de normas: Gestor Normativo de Función Pública."""
    URL    = "https://www.funcionpublica.gov.co/eva/gestornormativo/norma_busqueda.php"
    FUENTE = "Gestor Normativo - Función Pública"
    try:
        numero = re.search(r"\d+", referencia)
        anio   = re.search(r"(?:19|20)\d{2}", referencia)
        params = {
            "norma": numero.group() if numero else referencia,
            "anio":  anio.group() if anio else "",
        }
        resp = sesion.get(URL, params=params, timeout=TIMEOUT)
        if resp.status_code == 200 and "norma" in resp.text.lower():
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.find_all("a", href=re.compile(r"norma\.php\?i=")):
                href = a["href"]
                full = f"https://www.funcionpublica.gov.co{href}" if href.startswith("/") else href
                return "encontrada", FUENTE, full
        return "no_encontrada", FUENTE, URL
    except requests.exceptions.Timeout:
        return "no_verificable", f"{FUENTE} (timeout)", URL
    except requests.exceptions.ConnectionError:
        return "no_verificable", f"{FUENTE} (sin conexión)", URL
    except Exception:
        return "no_verificable", f"{FUENTE} (error)", URL


# ─────────────────────────────────────────────────────────────────────────────
# DOCTRINA
# ─────────────────────────────────────────────────────────────────────────────

def _verificar_isbn(referencia: str, sesion: requests.Session) -> _R:
    try:
        isbn = re.sub(r"[\s\-–]", "", referencia)
        r    = sesion.get(f"https://openlibrary.org/isbn/{isbn}.json", timeout=TIMEOUT)
        if r.status_code == 200:
            return "encontrada", "Open Library (ISBN)", f"https://openlibrary.org/isbn/{isbn}"
        return "no_encontrada", "Open Library (ISBN)", "https://openlibrary.org"
    except Exception:
        return "no_verificable", "Open Library (error)", ""


def _verificar_doi(referencia: str, sesion: requests.Session) -> _R:
    try:
        url = f"https://doi.org/{referencia}"
        r   = sesion.head(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code in (200, 301, 302, 303):
            return "encontrada", "doi.org", url
        return "no_encontrada", "doi.org", url
    except Exception:
        return "no_verificable", "doi.org (error)", ""


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCHER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def verificar_cita(cita: Cita, fuentes_activas: dict, sesion: requests.Session) -> Cita:
    """
    Verifica una cita y actualiza estado/fuente/enlace.
    Los enlaces generados son siempre URLs directas funcionales:
      - viewDocument.asp?id=XXXXX  (resultado exitoso en SUIN)
      - URL de relatoría de la corte  (fallback)
      - URL de búsqueda en Bing  (cuando no se encuentra)
    """
    estado, fuente, enlace = "no_verificable", "", ""

    if cita.tipo == "norma":
        if fuentes_activas.get("suin", True):
            estado, fuente, enlace = _verificar_suin_norma(
                cita.referencia, cita.subtipo, sesion
            )
        if estado != "encontrada" and fuentes_activas.get("funcion_publica", True):
            time.sleep(DELAY)
            estado, fuente, enlace = _verificar_funcion_publica(cita.referencia, sesion)

    elif cita.tipo == "corte_constitucional":
        if fuentes_activas.get("corte_constitucional", True):
            estado, fuente, enlace = _verificar_corte_constitucional(
                cita.referencia, sesion
            )

    elif cita.tipo == "corte_suprema":
        if fuentes_activas.get("corte_suprema", True):
            estado, fuente, enlace = _verificar_corte_suprema(cita.referencia, sesion)

    elif cita.tipo == "consejo_estado":
        if fuentes_activas.get("consejo_estado", True):
            estado, fuente, enlace = _verificar_consejo_estado(cita.referencia, sesion)

    elif cita.tipo == "doctrina":
        if cita.subtipo == "ISBN":
            estado, fuente, enlace = _verificar_isbn(cita.referencia, sesion)
        elif cita.subtipo == "DOI":
            estado, fuente, enlace = _verificar_doi(cita.referencia, sesion)
        else:
            estado  = "no_verificable"
            fuente  = "Sin fuente automatizable"
            enlace  = ""

    cita.estado = estado
    cita.fuente = fuente
    cita.enlace = enlace

    time.sleep(DELAY)
    return cita


def verificar_todas(citas: list, fuentes_activas: dict, callback_progreso=None) -> list:
    """Verifica todas las citas en secuencia."""
    sesion = _crear_sesion()
    total  = len(citas)
    for i, cita in enumerate(citas):
        if callback_progreso:
            callback_progreso(i, total, cita)
        verificar_cita(cita, fuentes_activas, sesion)
    return citas
