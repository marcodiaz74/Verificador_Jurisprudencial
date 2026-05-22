# verificador.py
# Verificación de citas en fuentes oficiales colombianas.
# Utiliza requests + BeautifulSoup con manejo robusto de errores
# y respeto de tiempos de espera para no saturar los servidores.

import time
import re
import requests
from bs4 import BeautifulSoup
from extractor import Cita

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE SESIÓN HTTP
# ──────────────────────────────────────────────────────────────────────────────

CABECERAS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; VerificadorJuridicoCol/1.0; "
        "+https://github.com/verificador-juridico-colombia)"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

TIMEOUT_SEGUNDOS = 12
DELAY_ENTRE_PETICIONES = 1.2  # segundos — buena práctica de scraping responsable


def _crear_sesion() -> requests.Session:
    sesion = requests.Session()
    sesion.headers.update(CABECERAS_HTTP)
    return sesion


# ──────────────────────────────────────────────────────────────────────────────
# VERIFICADORES POR FUENTE
# ──────────────────────────────────────────────────────────────────────────────

def _verificar_suin(referencia: str, subtipo: str, sesion: requests.Session) -> tuple[str, str, str]:
    """
    Verifica normas en SUIN-Juriscol (Sistema Único de Información Normativa).
    Retorna: (estado, fuente, enlace)
    """
    try:
        numero = re.search(r"\d+", referencia)
        anio = re.search(r"(?:19|20)\d{2}", referencia)

        if not numero:
            return "no_verificable", "SUIN-Juriscol", ""

        query_partes = []
        if subtipo:
            query_partes.append(subtipo)
        query_partes.append(numero.group())
        if anio:
            query_partes.append(anio.group())

        url_busqueda = (
            "https://www.suin-juriscol.gov.co/viewDocument.asp"
            f"?id={subtipo.replace(' ', '_')}_{numero.group()}_{anio.group() if anio else ''}"
        )

        # Búsqueda por texto libre en el buscador de SUIN
        url_api = (
            "https://www.suin-juriscol.gov.co/clp/contenidos.dll/Leyes"
            if subtipo.lower() == "ley"
            else "https://www.suin-juriscol.gov.co/clp/contenidos.dll/Decretos"
        )

        # Intentar URL directa estructurada
        url_directa = (
            f"https://www.suin-juriscol.gov.co/viewDocument.asp"
            f"?ruta=/clp/contenidos.dll/{subtipo.capitalize()}s/"
            f"{numero.group()}_{anio.group() if anio else ''}"
        )

        respuesta = sesion.get(
            "https://www.suin-juriscol.gov.co/legislacion/buscador.html",
            params={"q": " ".join(query_partes), "tipo": subtipo},
            timeout=TIMEOUT_SEGUNDOS
        )

        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.text, "lxml")
            # Buscar resultados en la página
            resultados = soup.find_all(["a", "li", "div"], string=re.compile(
                rf"{re.escape(numero.group())}.*{re.escape(anio.group()) if anio else ''}",
                re.IGNORECASE
            ))
            if resultados:
                href = resultados[0].get("href", "")
                enlace = f"https://www.suin-juriscol.gov.co{href}" if href.startswith("/") else href
                return "encontrada", "SUIN-Juriscol", enlace or "https://www.suin-juriscol.gov.co"
            # Si hay contenido pero no resultados explícitos, marcar como verificable
            if len(respuesta.text) > 1000:
                return "no_encontrada", "SUIN-Juriscol", "https://www.suin-juriscol.gov.co"

        return "no_encontrada", "SUIN-Juriscol", "https://www.suin-juriscol.gov.co"

    except requests.exceptions.Timeout:
        return "no_verificable", "SUIN-Juriscol (timeout)", ""
    except requests.exceptions.ConnectionError:
        return "no_verificable", "SUIN-Juriscol (sin conexión)", ""
    except Exception as e:
        return "no_verificable", f"SUIN-Juriscol (error: {str(e)[:40]})", ""


def _verificar_funcion_publica(referencia: str, sesion: requests.Session) -> tuple[str, str, str]:
    """Verifica normas en el Gestor Normativo de Función Pública."""
    try:
        url = "https://www.funcionpublica.gov.co/eva/gestornormativo/norma_busqueda.php"
        numero = re.search(r"\d+", referencia)
        anio = re.search(r"(?:19|20)\d{2}", referencia)

        params = {
            "norma": numero.group() if numero else referencia,
            "anio": anio.group() if anio else "",
        }

        respuesta = sesion.get(url, params=params, timeout=TIMEOUT_SEGUNDOS)

        if respuesta.status_code == 200 and "norma" in respuesta.text.lower():
            soup = BeautifulSoup(respuesta.text, "lxml")
            enlaces = soup.find_all("a", href=re.compile(r"norma\.php\?i="))
            if enlaces:
                href = enlaces[0]["href"]
                enlace_completo = f"https://www.funcionpublica.gov.co{href}" if href.startswith("/") else href
                return "encontrada", "Gestor Normativo - Función Pública", enlace_completo

        return "no_encontrada", "Gestor Normativo - Función Pública", url

    except requests.exceptions.Timeout:
        return "no_verificable", "Función Pública (timeout)", ""
    except requests.exceptions.ConnectionError:
        return "no_verificable", "Función Pública (sin conexión)", ""
    except Exception:
        return "no_verificable", "Función Pública (error)", ""


def _verificar_corte_constitucional(referencia: str, sesion: requests.Session) -> tuple[str, str, str]:
    """
    Verifica sentencias en la relatoría de la Corte Constitucional.
    Ejemplo: T-123/2020, C-456/2018
    """
    try:
        # Normalizar referencia: T-123/2020 o T-123/20
        match = re.match(r"([A-Z]+)-(\d+)/(\d{2,4})", referencia)
        if not match:
            return "no_verificable", "Corte Constitucional", ""

        tipo, numero, anio = match.groups()
        if len(anio) == 2:
            anio = ("19" if int(anio) > 50 else "20") + anio

        # URL de la relatoría
        url_relatoria = f"https://www.corteconstitucional.gov.co/relatoria/{anio}/{tipo}-{numero}.htm"
        url_busqueda = (
            "https://www.corteconstitucional.gov.co/relatoria/buscador_new/index_buscador.php"
        )

        # Intentar acceso directo
        try:
            resp_directa = sesion.get(url_relatoria, timeout=TIMEOUT_SEGUNDOS, allow_redirects=True)
            if resp_directa.status_code == 200 and len(resp_directa.text) > 500:
                return "encontrada", "Relatoría - Corte Constitucional", url_relatoria
        except Exception:
            pass

        # Búsqueda en el buscador oficial
        params = {
            "texto": f"{tipo}-{numero}",
            "Buscador": f"{tipo}-{numero}/{anio}",
        }
        resp_busqueda = sesion.get(url_busqueda, params=params, timeout=TIMEOUT_SEGUNDOS)

        if resp_busqueda.status_code == 200:
            soup = BeautifulSoup(resp_busqueda.text, "lxml")
            resultados = soup.find_all("a", string=re.compile(
                rf"{re.escape(tipo)}[\-–]{re.escape(numero)}", re.IGNORECASE
            ))
            if resultados:
                return "encontrada", "Relatoría - Corte Constitucional", url_relatoria

        return "no_encontrada", "Relatoría - Corte Constitucional", url_busqueda

    except requests.exceptions.Timeout:
        return "no_verificable", "Corte Constitucional (timeout)", ""
    except requests.exceptions.ConnectionError:
        return "no_verificable", "Corte Constitucional (sin conexión)", ""
    except Exception:
        return "no_verificable", "Corte Constitucional (error)", ""


def _verificar_corte_suprema(referencia: str, sesion: requests.Session) -> tuple[str, str, str]:
    """Verifica jurisprudencia en la relatoría de la Corte Suprema de Justicia."""
    try:
        url_relatoria = "https://cortesuprema.gov.co/corte/index.php/relatoria/"
        url_buscador = "https://cortesuprema.gov.co/corte/index.php/?s="

        # Limpiar referencia para búsqueda
        termino = referencia.replace("–", "-").strip()

        resp = sesion.get(
            url_buscador + requests.utils.quote(termino),
            timeout=TIMEOUT_SEGUNDOS
        )

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            resultados = soup.find_all(
                "a", string=re.compile(re.escape(termino.split("-")[0]), re.IGNORECASE)
            )
            if resultados:
                enlace = resultados[0].get("href", url_relatoria)
                return "encontrada", "Relatoría - Corte Suprema de Justicia", enlace

        return "no_encontrada", "Relatoría - Corte Suprema de Justicia", url_relatoria

    except requests.exceptions.Timeout:
        return "no_verificable", "Corte Suprema (timeout)", ""
    except requests.exceptions.ConnectionError:
        return "no_verificable", "Corte Suprema (sin conexión)", ""
    except Exception:
        return "no_verificable", "Corte Suprema (error)", ""


def _verificar_consejo_estado(referencia: str, sesion: requests.Session) -> tuple[str, str, str]:
    """Verifica jurisprudencia en el buscador del Consejo de Estado."""
    try:
        url_buscador = "https://www.consejodeestado.gov.co/busquedas/buscador-jurisprudencia/"

        resp = sesion.get(
            url_buscador,
            params={"q": referencia},
            timeout=TIMEOUT_SEGUNDOS
        )

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            resultados = soup.find_all(
                ["a", "div", "li"],
                string=re.compile(re.escape(referencia[:15]), re.IGNORECASE)
            )
            if resultados:
                enlace = resultados[0].get("href", url_buscador) if resultados[0].name == "a" else url_buscador
                return "encontrada", "Buscador Jurisprudencial - Consejo de Estado", enlace

        return "no_encontrada", "Buscador Jurisprudencial - Consejo de Estado", url_buscador

    except requests.exceptions.Timeout:
        return "no_verificable", "Consejo de Estado (timeout)", ""
    except requests.exceptions.ConnectionError:
        return "no_verificable", "Consejo de Estado (sin conexión)", ""
    except Exception:
        return "no_verificable", "Consejo de Estado (error)", ""


def _verificar_isbn(referencia: str, sesion: requests.Session) -> tuple[str, str, str]:
    """Verifica ISBN usando la API pública de Open Library."""
    try:
        isbn_limpio = re.sub(r"[\s\-–]", "", referencia)
        url = f"https://openlibrary.org/isbn/{isbn_limpio}.json"
        resp = sesion.get(url, timeout=TIMEOUT_SEGUNDOS)
        if resp.status_code == 200:
            return "encontrada", "Open Library (ISBN)", f"https://openlibrary.org/isbn/{isbn_limpio}"
        return "no_encontrada", "Open Library (ISBN)", "https://openlibrary.org"
    except Exception:
        return "no_verificable", "Open Library (error)", ""


def _verificar_doi(referencia: str, sesion: requests.Session) -> tuple[str, str, str]:
    """Verifica DOI usando doi.org."""
    try:
        url = f"https://doi.org/{referencia}"
        resp = sesion.head(url, timeout=TIMEOUT_SEGUNDOS, allow_redirects=True)
        if resp.status_code in (200, 301, 302, 303):
            return "encontrada", "doi.org", url
        return "no_encontrada", "doi.org", url
    except Exception:
        return "no_verificable", "doi.org (error)", ""


# ──────────────────────────────────────────────────────────────────────────────
# DISPATCHER PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

def verificar_cita(
    cita: Cita,
    fuentes_activas: dict[str, bool],
    sesion: requests.Session,
) -> Cita:
    """
    Verifica una cita individual contra las fuentes oficiales seleccionadas.
    Modifica la cita in-place y la retorna.
    """
    estado, fuente, enlace = "no_verificable", "", ""

    if cita.tipo == "norma":
        if fuentes_activas.get("suin", True):
            estado, fuente, enlace = _verificar_suin(cita.referencia, cita.subtipo, sesion)
        if estado != "encontrada" and fuentes_activas.get("funcion_publica", True):
            time.sleep(DELAY_ENTRE_PETICIONES)
            estado, fuente, enlace = _verificar_funcion_publica(cita.referencia, sesion)

    elif cita.tipo == "corte_constitucional":
        if fuentes_activas.get("corte_constitucional", True):
            estado, fuente, enlace = _verificar_corte_constitucional(cita.referencia, sesion)

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
            estado, fuente, enlace = "no_verificable", "Sin fuente automatizable", ""

    cita.estado = estado
    cita.fuente = fuente
    cita.enlace = enlace

    time.sleep(DELAY_ENTRE_PETICIONES)
    return cita


def verificar_todas(
    citas: list[Cita],
    fuentes_activas: dict[str, bool],
    callback_progreso=None,
) -> list[Cita]:
    """
    Verifica todas las citas en secuencia.
    callback_progreso(i, total, cita): función opcional para actualizar UI.
    """
    sesion = _crear_sesion()
    total = len(citas)

    for i, cita in enumerate(citas):
        if callback_progreso:
            callback_progreso(i, total, cita)
        verificar_cita(cita, fuentes_activas, sesion)

    return citas
