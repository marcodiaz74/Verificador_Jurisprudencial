# anonimizador.py
# Módulo de protección de datos personales
# Cumplimiento: Ley 1581 de 2012 (Habeas Data), Ley 1266 de 2008,
# Decreto 1377 de 2013 y principios de IA responsable en el sistema jurídico colombiano.

import re
import hashlib

# ──────────────────────────────────────────────
# PATRONES DE DATOS SENSIBLES Y PERSONALES
# ──────────────────────────────────────────────

PATRONES_DATOS_PERSONALES = {
    # Identificación personal
    "cedula": re.compile(
        r"\b(?:C\.?C\.?|cédula\s+de\s+ciudadanía|cedula)\s*[Nn](?:o|°|\.)?\.?\s*\d[\d\.\s]{5,12}\b",
        re.IGNORECASE
    ),
    "nit": re.compile(
        r"\b(?:NIT|N\.I\.T\.)\s*[Nn](?:o|°|\.)?\.?\s*\d[\d\.\-]{5,14}\b",
        re.IGNORECASE
    ),
    "tarjeta_identidad": re.compile(
        r"\b(?:T\.?I\.?|tarjeta\s+de\s+identidad)\s*[Nn](?:o|°|\.)?\.?\s*\d[\d\.\s]{5,12}\b",
        re.IGNORECASE
    ),
    "pasaporte": re.compile(
        r"\b(?:pasaporte|passport)\s*[Nn](?:o|°|\.)?\.?\s*[A-Z]{1,2}\d{5,9}\b",
        re.IGNORECASE
    ),
    "registro_civil": re.compile(
        r"\b(?:registro\s+civil)\s*[Nn](?:o|°|\.)?\.?\s*\d[\d\s]{5,14}\b",
        re.IGNORECASE
    ),

    # Contacto
    "correo_electronico": re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
    ),
    "telefono": re.compile(
        r"\b(?:\+57[\s\-]?)?(?:3[0-2]\d|60[1-8]|[1-8])[\s\-]?\d{3}[\s\-]?\d{4}\b"
    ),

    # Dirección física
    "direccion": re.compile(
        r"\b(?:Calle|Carrera|Avenida|Diagonal|Transversal|Cra|Cl|Av|Dg|Tv)\.?\s*\d+\w*\s*[#\-]\s*\d+\w*(?:\s*\-\s*\d+\w*)?\b",
        re.IGNORECASE
    ),

    # Datos financieros
    "cuenta_bancaria": re.compile(
        r"\b(?:cuenta\s+(?:bancaria|de\s+ahorros|corriente|nómina)|IBAN)\s*[Nn](?:o|°|\.)?\.?\s*\d[\d\s]{8,20}\b",
        re.IGNORECASE
    ),
    "tarjeta_credito": re.compile(
        r"\b(?:4[0-9]{3}|5[1-5][0-9]{2}|3[47][0-9]{2}|6(?:011|5[0-9]{2}))[\ \-]?\d{4}[\ \-]?\d{4}[\ \-]?\d{4}\b"
    ),

    # Datos de salud (categoría especial — art. 6 Ley 1581/2012)
    "diagnostico": re.compile(
        r"\b(?:diagnóstico|diagnostico|patología|patologia|enfermedad|padece\s+de|sufre\s+de|tratamiento\s+médico)\s*[:\-]?\s*[A-Za-záéíóúñÁÉÍÓÚÑ\s]{3,50}",
        re.IGNORECASE
    ),

    # Datos biométricos
    "huella": re.compile(
        r"\b(?:huella\s+(?:dactilar|digital)|biométrico|biometrico|dactiloscopía)\b",
        re.IGNORECASE
    ),

    # Nombres propios (heurística conservadora: 2-4 palabras capitalizadas no al inicio de frase)
    "nombre_propio": re.compile(
        r"(?<![.!?]\s)(?<!\n)\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}){1,3})\b"
    ),
}

# Términos jurídicos y entidades institucionales que NO deben anonimizarse
EXCEPCIONES_INSTITUCIONALES = {
    "Corte Constitucional", "Corte Suprema", "Consejo de Estado",
    "Consejo Superior", "Tribunal Superior", "Juzgado", "Fiscalía",
    "Procuraduría", "Contraloría", "Defensoría", "Ministerio",
    "Superintendencia", "Congreso", "Senado", "Colombia", "República",
    "Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena",
    "Presidente", "Magistrado", "Magistrada", "Doctor", "Doctora",
    "Sala Civil", "Sala Laboral", "Sala Penal", "Sala Plena",
    "Sección Primera", "Sección Segunda", "Sección Tercera",
    "Sección Cuarta", "Sección Quinta",
}


def _es_excepcion_institucional(texto: str) -> bool:
    """Verifica si el texto corresponde a una entidad institucional exceptuada."""
    for excepcion in EXCEPCIONES_INSTITUCIONALES:
        if excepcion.lower() in texto.lower():
            return True
    return False


def _hash_referencia(valor: str) -> str:
    """Genera una referencia irreversible para trazabilidad interna."""
    return "[REF-" + hashlib.sha256(valor.encode()).hexdigest()[:8].upper() + "]"


def anonimizar_texto(texto: str) -> tuple[str, dict]:
    """
    Aplica anonimización al texto siguiendo los principios de la Ley 1581/2012.

    Retorna:
        texto_anonimizado (str): Texto con datos personales reemplazados.
        registro_reemplazos (dict): Conteo de reemplazos por categoría (sin los valores originales).
    """
    texto_procesado = texto
    registro = {}

    for categoria, patron in PATRONES_DATOS_PERSONALES.items():
        coincidencias = patron.findall(texto_procesado)
        reemplazos = 0

        for coincidencia in coincidencias:
            valor = coincidencia if isinstance(coincidencia, str) else coincidencia[0]

            # Respetar excepciones institucionales
            if _es_excepcion_institucional(valor):
                continue

            # Para nombres propios, aplicar heurística adicional
            if categoria == "nombre_propio":
                palabras = valor.strip().split()
                if len(palabras) < 2:
                    continue
                # Excluir si alguna palabra es una excepción institucional
                if any(_es_excepcion_institucional(p) for p in palabras):
                    continue

            etiqueta = f"[DATO PERSONAL - {categoria.upper().replace('_', ' ')}]"
            texto_procesado = texto_procesado.replace(valor, etiqueta, 1)
            reemplazos += 1

        if reemplazos > 0:
            registro[categoria] = reemplazos

    return texto_procesado, registro


def generar_advertencia_habeas_data() -> str:
    """Retorna el texto de advertencia legal que debe mostrarse al usuario."""
    return (
        "⚖️ **Aviso de protección de datos — Habeas Data**\n\n"
        "Esta aplicación procesa documentos jurídicos que pueden contener "
        "datos personales protegidos por la **Ley 1581 de 2012** y la "
        "**Ley 1266 de 2008**. En cumplimiento del principio de minimización "
        "y del derecho al Habeas Data:\n\n"
        "- Los datos personales identificables (nombres, cédulas, direcciones, "
        "teléfonos, correos, datos de salud, etc.) son **anonimizados automáticamente** "
        "antes de cualquier procesamiento.\n"
        "- **Ningún dato personal es almacenado**, transmitido a servidores externos "
        "ni compartido con terceros.\n"
        "- El procesamiento se realiza **únicamente en memoria** durante la sesión activa.\n"
        "- Esta herramienta aplica principios de **IA responsable**: transparencia, "
        "no discriminación y supervisión humana. Las verificaciones son orientativas "
        "y no reemplazan el criterio del profesional jurídico.\n\n"
        "📌 *Al cargar un documento, usted confirma que tiene autorización para "
        "procesarlo y acepta estas condiciones.*"
    )


def resumen_anonimizacion(registro: dict) -> str:
    """Genera un resumen legible de los datos anonimizados."""
    if not registro:
        return "✅ No se detectaron datos personales identificables en el documento."

    total = sum(registro.values())
    lineas = [f"🔒 Se anonimizaron **{total}** dato(s) personal(es):"]
    etiquetas = {
        "cedula": "Cédulas de ciudadanía",
        "nit": "NIT",
        "tarjeta_identidad": "Tarjetas de identidad",
        "pasaporte": "Pasaportes",
        "registro_civil": "Registros civiles",
        "correo_electronico": "Correos electrónicos",
        "telefono": "Teléfonos",
        "direccion": "Direcciones físicas",
        "cuenta_bancaria": "Cuentas bancarias",
        "tarjeta_credito": "Tarjetas de crédito",
        "diagnostico": "Diagnósticos médicos (dato sensible)",
        "huella": "Referencias biométricas (dato sensible)",
        "nombre_propio": "Nombres de personas naturales",
    }
    for cat, cantidad in registro.items():
        nombre = etiquetas.get(cat, cat.replace("_", " ").capitalize())
        lineas.append(f"  - {nombre}: {cantidad}")
    return "\n".join(lineas)
