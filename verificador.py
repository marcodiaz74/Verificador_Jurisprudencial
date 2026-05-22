# verificador.py
# Verificación de providencias judiciales colombianas en SUIN-Juriscol.
#
# Corte Constitucional  → SUIN-Juriscol (corporacion=200) + relatoria propia como fallback
# Corte Suprema de Justicia → SUIN-Juriscol (corporacion=300)
# Consejo de Estado     → SUIN-Juriscol (corporacion=100)
# Normas                → SUIN-Juriscol buscador normativo + Función Pública
#
# Códigos de corporación confirmados en los metadatos de SUIN:
#   100 → Consejo de Estado
#   200 → Corte Constitucional
#   300 → Corte Suprema de Justicia

import re
import time
import urllib3
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
from extractor import Cita

# ── Suprimir advertencia de SSL — SUIN tiene cadena de cert incompleta ────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Constantes ────────────────────────────────────────────────────────────────
BASE_SUIN   = "https://www.suin-juriscol.gov.co"
URL_BUSCADOR_JURISP = f"{BASE_SUIN}/jurisprudencia/buscador.html"
URL_JURISP_HOME     = f"{BASE_SUIN}/jurisprudencia/jurisprudencia.html"
TIMEOUT     = 15      # segundos por petición
DELAY       = 1.2     # segundos entre peticiones (cortesía con el servidor)

# Código de corporación en el formulario de SUIN
COD_CONSEJO_ESTADO   = "100"
COD_CORTE_CONST      = "200"
COD_CORTE_SUPREMA    = "300"

CABECERAS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Tipo de retorno abreviado
_R = tuple[str, str, str]   # (estado, fuente, enlace)


# ── Sesión HTTP ───────────────────────────────────────────────────────────────

def _crear_sesion() -> requests.Session:
    s = requests.Session()
    s.headers.update(CABECERAS)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# HELPER GENÉRICO: buscar en SUIN por número de providencia y corporación
# ─────────────────────────────────────────────────────────────────────────────

def _buscar_en_suin(
    numero_providencia: str,
    corporacion: str,
    fuente_nombre: str,
    sesion: requests.Session,
    anio: str = "",
) -> _R:
    """
    Consulta el buscador de jurisprudencia de SUIN-Juriscol.

    Parámetros del formulario real observados en SUIN:
      numero_providencia  → número/radicado de la providencia
      corporacion         → 100 (CE), 200 (CC), 300 (CSJ)
      anio                → año de la providencia (opcional)
      tipo_providencia    → vacío para buscar todos los tipos

    Retorna (estado, fuente, enlace).
    """
    params = {
        "numero_providencia": numero_providencia,
        "corporacion":        corporacion,
        "tipo_providencia":   "",
        "anio":               anio,
        "tema":               "",
    }

    try:
        resp = sesion.get(
            URL_BUSCADOR_JURISP,
            params=params,
            timeout=TIMEOUT,
            verify=False,
        )
        if resp.status_code != 200 or len(resp.text) < 400:
            return "no_verificable", fuente_nombre, URL_JURISP_HOME

        soup = BeautifulSoup(resp.text, "lxml")

        # Los resultados son enlaces a viewDocument.asp?id=XXXXXXXX
        enlaces = soup.find_all(
            "a",
            href=re.compile(r"viewDocument\.asp\?id=\d+", re.IGNORECASE),
        )
        if enlaces:
            href = enlaces[0]["href"]
            url_doc = href if href.startswith("http") else f"{BASE_SUIN}/{href.lstrip('/')}"
            return "encontrada", fuente_nombre, url_doc

        # Detectar mensaje explícito de "sin resultados"
        texto = soup.get_text(" ").lower()
        if any(f in texto for f in [
            "no se encontr", "sin resultado", "0 resultado",
            "ningún resultado", "no hay providencia", "no existen"
        ]):
            url_manual = f"{URL_BUSCADOR_JURISP}?numero_providencia={quote(numero_providencia)}&corporacion={corporacion}"
            return "no_encontrada", fuente_nombre, url_manual

        # Respuesta ambigua: devolver como no_verificable con link al buscador
        url_manual = f"{URL_BUSCADOR_JURISP}?numero_providencia={quote(numero_providencia)}&corporacion={corporacion}"
        return "no_verificable", fuente_nombre, url_manual

    except requests.exceptions.Timeout:
        return "no_verificable", f"{fuente_nombre} (timeout)", URL_JURISP_HOME
    except requests.exceptions.ConnectionError:
        return "no_verificable", f"{fuente_nombre} (sin conexión)", URL_JURISP_HOME
    except Exception as e:
        return "no_verificable", f"{fuente_nombre} (error)", URL_JURISP_HOME


# ─────────────────────────────────────────────────────────────────────────────
# CORTE CONSTITUCIONAL — SUIN + fallback a relatoría propia
# ─────────────────────────────────────────────────────────────────────────────

def _verificar_corte_constitucional(referencia: str, sesion: requests.Session) -> _R:
    """
    Verifica providencias de la Corte Constitucional.

    Estrategia:
    1. Buscar en SUIN-Juriscol (corporacion=200) con el identificador de la sentencia.
    2. Fallback: acceso directo a la relatoría de la Corte Constitucional.

    La referencia puede ser: T-123/2020, C-456/18, SU-123/2021, A-045/2019, D-15000
    """
    FUENTE = "SUIN-Juriscol · Corte Constitucional (cod. 200)"

    # ── Normalizar: extraer tipo, número y año ───────────────────────────────
    match = re.match(
        r"([A-Z]+)[\-–](\d{1,4})(?:[/\-](\d{2,4}))?",
        referencia.strip(),
    )
    if not match:
        return "no_verificable", FUENTE, URL_JURISP_HOME

    tipo, numero, anio_raw = match.groups()
    anio = ""
    if anio_raw:
        anio = ("20" if len(anio_raw) == 2 and int(anio_raw) <= 25 else
                "19" if len(anio_raw) == 2 else "") + anio_raw

    # ── Capa 1: SUIN con identificador completo (ej. "T-123") ────────────────
    identificador = f"{tipo}-{numero}"
    estado, fuente, enlace = _buscar_en_suin(
        identificador, COD_CORTE_CONST, FUENTE, sesion, anio=anio
    )
    if estado == "encontrada":
        return estado, fuente, enlace

    # ── Capa 2: SUIN con sólo el número (algunos registros se indexan así) ───
    time.sleep(DELAY)
    estado2, fuente2, enlace2 = _buscar_en_suin(
        numero, COD_CORTE_CONST, FUENTE, sesion, anio=anio
    )
    if estado2 == "encontrada":
        return estado2, fuente2, enlace2

    # ── Capa 3: Acceso directo a la relatoría de la Corte Constitucional ─────
    if anio:
        url_directa = f"https://www.corteconstitucional.gov.co/relatoria/{anio}/{tipo}-{numero}.htm"
        try:
            time.sleep(DELAY)
            r = sesion.get(url_directa, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200 and len(r.text) > 500:
                return (
                    "encontrada",
                    "Relatoría Corte Constitucional (fallback)",
                    url_directa,
                )
        except Exception:
            pass

    # No encontrada — devolver link al buscador de SUIN para revisión manual
    url_manual = (
        f"{URL_BUSCADOR_JURISP}"
        f"?numero_providencia={quote(identificador)}&corporacion={COD_CORTE_CONST}"
    )
    return "no_encontrada", FUENTE, url_manual


# ─────────────────────────────────────────────────────────────────────────────
# CORTE SUPREMA DE JUSTICIA — SUIN
# ─────────────────────────────────────────────────────────────────────────────

def _limpiar_ref_csj(referencia: str) -> tuple[str, str]:
    """
    Extrae el número de radicado/providencia y el año de una referencia de la CSJ.
    Ejemplos:
      SC1234-2021  → ("SC1234", "2021")  o  ("1234", "2021")
      SL5678-2019  → ("5678", "2019")
      SP9012-2020  → ("9012", "2020")
      Rad. 45678   → ("45678", "")
    """
    ref = referencia.strip().replace("–", "-").replace("—", "-")

    # Formato SC/SL/SP NNNN-YYYY
    m = re.match(r"(SC|SL|SP)\s*(\d+)[-–](\d{4})", ref, re.IGNORECASE)
    if m:
        return m.group(2), m.group(3)

    # Sólo radicado numérico
    m2 = re.search(r"(\d{5,})", ref)
    anio_m = re.search(r"((?:19|20)\d{2})", ref)
    if m2:
        return m2.group(1), (anio_m.group(1) if anio_m else "")

    return ref, ""


def _verificar_corte_suprema(referencia: str, sesion: requests.Session) -> _R:
    """
    Verifica sentencias de la Corte Suprema de Justicia en SUIN-Juriscol (cod. 300).

    Estrategia en dos capas:
    1. SUIN con el número extraído de la referencia.
    2. SUIN con la referencia original limpia.
    """
    FUENTE = "SUIN-Juriscol · Corte Suprema de Justicia (cod. 300)"

    numero, anio = _limpiar_ref_csj(referencia)

    # ── Capa 1: búsqueda con número extraído ─────────────────────────────────
    estado, fuente, enlace = _buscar_en_suin(
        numero, COD_CORTE_SUPREMA, FUENTE, sesion, anio=anio
    )
    if estado == "encontrada":
        return estado, fuente, enlace

    # ── Capa 2: búsqueda con referencia original normalizada ─────────────────
    ref_limpia = referencia.strip().replace("–", "-").replace("—", "-")
    if ref_limpia != numero:
        time.sleep(DELAY)
        estado2, fuente2, enlace2 = _buscar_en_suin(
            ref_limpia, COD_CORTE_SUPREMA, FUENTE, sesion, anio=anio
        )
        if estado2 == "encontrada":
            return estado2, fuente2, enlace2

    url_manual = (
        f"{URL_BUSCADOR_JURISP}"
        f"?numero_providencia={quote(numero)}&corporacion={COD_CORTE_SUPREMA}"
    )
    return "no_encontrada", FUENTE, url_manual


# ─────────────────────────────────────────────────────────────────────────────
# CONSEJO DE ESTADO — SUIN
# ─────────────────────────────────────────────────────────────────────────────

def _limpiar_radicado_ce(referencia: str) -> tuple[str, str]:
    """
    Normaliza el radicado del Consejo de Estado.
    Devuelve (radicado_para_busqueda, radicado_con_guiones).
    Ejemplos:
      '11001-03-24-000-2019-00319-00' → ('11001032400020190031900', '11001-03-24-000-2019-00319-00')
      'Exp. 47685'                    → ('47685', '47685')
    """
    ref = re.sub(
        r"(?:Exp(?:ediente)?|Rad(?:icado)?|No?)[.\s]*", "", referencia, flags=re.IGNORECASE
    ).strip()

    # Radicado largo con guiones — conservar ambas versiones
    if re.match(r"\d{5}[-–]\d{2}[-–]\d{2}[-–]\d{3}[-–]\d{4}[-–]\d{5}[-–]\d{2}", ref):
        sin_guiones = re.sub(r"[\-–\s]", "", ref)
        return sin_guiones, ref.replace("–", "-")

    # Radicado numérico simple
    solo_num = re.sub(r"[\s\-–]", "", ref)
    return (solo_num if solo_num.isdigit() else ref), ref


def _verificar_consejo_estado(referencia: str, sesion: requests.Session) -> _R:
    """
    Verifica providencias del Consejo de Estado en SUIN-Juriscol (cod. 100).

    Estrategia en tres capas:
    1. SUIN con radicado sin guiones (formato numérico continuo).
    2. SUIN con radicado con guiones (formato original largo).
    3. SUIN búsqueda texto libre si las anteriores fallan.
    """
    FUENTE = "SUIN-Juriscol · Consejo de Estado (cod. 100)"

    radicado_num, radicado_guiones = _limpiar_radicado_ce(referencia)

    # ── Capa 1 ────────────────────────────────────────────────────────────────
    estado, fuente, enlace = _buscar_en_suin(
        radicado_num, COD_CONSEJO_ESTADO, FUENTE, sesion
    )
    if estado == "encontrada":
        return estado, fuente, enlace

    # ── Capa 2 (solo si el radicado largo difiere del numérico) ───────────────
    if radicado_guiones != radicado_num:
        time.sleep(DELAY)
        estado2, fuente2, enlace2 = _buscar_en_suin(
            radicado_guiones, COD_CONSEJO_ESTADO, FUENTE, sesion
        )
        if estado2 == "encontrada":
            return estado2, fuente2, enlace2

    # ── Capa 3: texto libre en la sección CE de SUIN ──────────────────────────
    try:
        time.sleep(DELAY)
        url_tl = f"{BASE_SUIN}/clp/contenidos.dll/Jurisprudencia/CE"
        r = sesion.get(url_tl, params={"texto": radicado_num}, timeout=TIMEOUT, verify=False)
        if r.status_code == 200 and len(r.text) > 400:
            soup = BeautifulSoup(r.text, "lxml")
            enlaces = soup.find_all(
                "a", href=re.compile(r"viewDocument\.asp\?id=\d+", re.IGNORECASE)
            )
            if enlaces:
                href = enlaces[0]["href"]
                url_doc = href if href.startswith("http") else f"{BASE_SUIN}/{href.lstrip('/')}"
                return "encontrada", FUENTE, url_doc
    except Exception:
        pass

    url_manual = (
        f"{URL_BUSCADOR_JURISP}"
        f"?numero_providencia={quote(radicado_num)}&corporacion={COD_CONSEJO_ESTADO}"
    )
    return "no_encontrada", FUENTE, url_manual


# ─────────────────────────────────────────────────────────────────────────────
# NORMAS — SUIN + Función Pública
# ─────────────────────────────────────────────────────────────────────────────

def _verificar_suin_norma(referencia: str, subtipo: str, sesion: requests.Session) -> _R:
    """Verifica normas legales en el buscador normativo de SUIN-Juriscol."""
    URL_NORM = f"{BASE_SUIN}/legislacion/buscador.html"
    FUENTE   = "SUIN-Juriscol (normas)"
    try:
        numero = re.search(r"\d+", referencia)
        anio   = re.search(r"(?:19|20)\d{2}", referencia)
        if not numero:
            return "no_verificable", FUENTE, URL_NORM

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
                url_doc = href if href.startswith("http") else f"{BASE_SUIN}/{href.lstrip('/')}"
                return "encontrada", FUENTE, url_doc

        return "no_encontrada", FUENTE, URL_NORM

    except requests.exceptions.Timeout:
        return "no_verificable", f"{FUENTE} (timeout)", URL_NORM
    except requests.exceptions.ConnectionError:
        return "no_verificable", f"{FUENTE} (sin conexión)", URL_NORM
    except Exception:
        return "no_verificable", f"{FUENTE} (error)", URL_NORM


def _verificar_funcion_publica(referencia: str, sesion: requests.Session) -> _R:
    """Verifica normas en el Gestor Normativo de Función Pública (fallback)."""
    URL = "https://www.funcionpublica.gov.co/eva/gestornormativo/norma_busqueda.php"
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
            enlaces = soup.find_all("a", href=re.compile(r"norma\.php\?i="))
            if enlaces:
                href = enlaces[0]["href"]
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
# DOCTRINA — ISBN y DOI
# ─────────────────────────────────────────────────────────────────────────────

def _verificar_isbn(referencia: str, sesion: requests.Session) -> _R:
    try:
        isbn = re.sub(r"[\s\-–]", "", referencia)
        url  = f"https://openlibrary.org/isbn/{isbn}.json"
        r    = sesion.get(url, timeout=TIMEOUT)
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

def verificar_cita(
    cita: Cita,
    fuentes_activas: dict,
    sesion: requests.Session,
) -> Cita:
    """
    Verifica una cita individual y actualiza sus campos estado/fuente/enlace.

    Tabla de fuentes:
      norma             → SUIN (normas) + Función Pública (fallback)
      corte_constitucional → SUIN cod.200 + relatoría CC (fallback)
      corte_suprema     → SUIN cod.300
      consejo_estado    → SUIN cod.100
      doctrina          → Open Library (ISBN) / doi.org (DOI)
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
            fuente  = "Sin fuente automatizable para este tipo de doctrina"
            enlace  = ""

    cita.estado = estado
    cita.fuente = fuente
    cita.enlace = enlace

    time.sleep(DELAY)
    return cita


def verificar_todas(
    citas: list,
    fuentes_activas: dict,
    callback_progreso=None,
) -> list:
    """Verifica todas las citas en secuencia con delay entre peticiones."""
    sesion = _crear_sesion()
    total  = len(citas)
    for i, cita in enumerate(citas):
        if callback_progreso:
            callback_progreso(i, total, cita)
        verificar_cita(cita, fuentes_activas, sesion)
    return citas
