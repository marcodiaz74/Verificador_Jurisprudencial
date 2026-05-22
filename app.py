# app.py
# Verificador de Citas Jurídicas Colombianas
# Desarrollado con Streamlit — desplegable en Streamlit Community Cloud
#
# Cumplimiento legal:
#   - Ley 1581 de 2012 (Habeas Data / Protección de datos personales)
#   - Ley 1266 de 2008 (Información financiera)
#   - Decreto 1377 de 2013
#   - Principios de IA responsable: transparencia, supervisión humana,
#     no discriminación, minimización de datos.

import streamlit as st
import pandas as pd
import time

# Módulos propios
from anonimizador import (
    anonimizar_texto,
    generar_advertencia_habeas_data,
    resumen_anonimizacion,
)
from extractor import extraer_citas, agrupar_por_tipo, ETIQUETAS_TIPO
from verificador import verificar_todas
from utils import (
    extraer_texto,
    limpiar_texto,
    citas_a_dataframe,
    exportar_excel,
    calcular_estadisticas,
    ETIQUETAS_ESTADO,
    ETIQUETAS_TIPO_CORTO,
)

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Verificador de Citas Jurídicas · Colombia",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# ESTILOS PERSONALIZADOS
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Source+Sans+3:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Source Sans 3', sans-serif;
}

/* Encabezado principal */
.encabezado-principal {
    background: linear-gradient(135deg, #0d1b2a 0%, #1b3a5c 60%, #2a5c8a 100%);
    padding: 2rem 2.5rem 1.5rem 2.5rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 24px rgba(13,27,42,0.35);
}
.encabezado-principal h1 {
    font-family: 'Playfair Display', serif;
    color: #e8d9b5;
    font-size: 2rem;
    margin: 0 0 0.25rem 0;
    letter-spacing: 0.02em;
}
.encabezado-principal p {
    color: #a8c4e0;
    font-size: 0.95rem;
    margin: 0;
}

/* Tarjetas de métricas */
.metrica-card {
    background: #f8f9fb;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    border-left: 5px solid #1b3a5c;
    margin-bottom: 0.8rem;
}
.metrica-card.verde { border-left-color: #1a7a4a; }
.metrica-card.rojo { border-left-color: #c0392b; }
.metrica-card.amarillo { border-left-color: #d4a017; }

/* Tabla de resultados con colores */
.estado-encontrada { color: #1a7a4a; font-weight: 600; }
.estado-no_encontrada { color: #c0392b; font-weight: 600; }
.estado-no_verificable { color: #b7860b; font-weight: 600; }

/* Aviso legal */
.aviso-legal {
    background: #fffbf0;
    border: 1px solid #d4a017;
    border-radius: 8px;
    padding: 1rem;
    font-size: 0.88rem;
    color: #5a4a00;
    margin-bottom: 1rem;
}

/* Insignia de IA responsable */
.badge-ia {
    display: inline-block;
    background: #e8f4f8;
    color: #1b5c7a;
    border: 1px solid #a8cfe0;
    border-radius: 20px;
    padding: 0.2rem 0.8rem;
    font-size: 0.78rem;
    font-weight: 600;
    margin-top: 0.5rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0d1b2a;
}
section[data-testid="stSidebar"] * {
    color: #d0dde8 !important;
}
section[data-testid="stSidebar"] .stCheckbox span { color: #d0dde8 !important; }

/* Tabs */
button[data-baseweb="tab"] {
    font-family: 'Source Sans 3', sans-serif;
    font-size: 0.95rem;
}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# ENCABEZADO
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="encabezado-principal">
  <h1>⚖️ Verificador de Citas Jurídicas Colombianas</h1>
  <p>Detección y verificación automática de normas, jurisprudencia y doctrina en documentos legales.</p>
  <span class="badge-ia">🤖 IA Responsable · Habeas Data · Uso orientativo</span>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# BARRA LATERAL (SIDEBAR)
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    st.markdown("---")

    st.markdown("### 🔎 Tipos de cita a detectar")
    filtro_normas = st.checkbox("📜 Normas legales", value=True)
    filtro_cc = st.checkbox("⚖️ Corte Constitucional", value=True)
    filtro_csj = st.checkbox("🏛️ Corte Suprema de Justicia", value=True)
    filtro_ce = st.checkbox("🏢 Consejo de Estado", value=True)
    filtro_doctrina = st.checkbox("📚 Doctrina (ISBN / DOI)", value=True)

    st.markdown("---")
    st.markdown("### 🌐 Fuentes de verificación")
    fuente_suin = st.checkbox("SUIN-Juriscol", value=True)
    fuente_fp = st.checkbox("Función Pública", value=True)
    fuente_cc_web = st.checkbox("Corte Constitucional", value=True)
    fuente_csj_web = st.checkbox("Corte Suprema", value=True)
    fuente_ce_web = st.checkbox("Consejo de Estado", value=True)

    fuentes_activas = {
        "suin": fuente_suin,
        "funcion_publica": fuente_fp,
        "corte_constitucional": fuente_cc_web,
        "corte_suprema": fuente_csj_web,
        "consejo_estado": fuente_ce_web,
    }

    st.markdown("---")
    st.markdown("### 🔒 Privacidad")
    anonimizar = st.toggle("Anonimizar datos personales", value=True,
                           help="Elimina nombres, cédulas, teléfonos, etc. antes del análisis (recomendado)")

    st.markdown("---")
    st.caption(
        "Esta herramienta es de uso orientativo. "
        "No reemplaza el criterio del profesional jurídico ni constituye concepto legal. "
        "Cumple con Ley 1581/2012 y principios de IA responsable."
    )


# ──────────────────────────────────────────────────────────────────────────────
# AVISO DE HABEAS DATA (siempre visible)
# ──────────────────────────────────────────────────────────────────────────────

with st.expander("⚖️ Aviso legal — Habeas Data e IA Responsable", expanded=False):
    st.markdown(generar_advertencia_habeas_data())

st.markdown("---")


# ──────────────────────────────────────────────────────────────────────────────
# ESTADO DE SESIÓN
# ──────────────────────────────────────────────────────────────────────────────

if "texto_anonimizado" not in st.session_state:
    st.session_state.texto_anonimizado = ""
if "texto_original_display" not in st.session_state:
    st.session_state.texto_original_display = ""
if "citas" not in st.session_state:
    st.session_state.citas = []
if "citas_verificadas" not in st.session_state:
    st.session_state.citas_verificadas = False
if "nombre_archivo" not in st.session_state:
    st.session_state.nombre_archivo = ""
if "registro_anonimizacion" not in st.session_state:
    st.session_state.registro_anonimizacion = {}


# ──────────────────────────────────────────────────────────────────────────────
# PESTAÑAS PRINCIPALES
# ──────────────────────────────────────────────────────────────────────────────

tab_doc, tab_citas, tab_verificacion, tab_reporte = st.tabs([
    "📄 Documento",
    "🔍 Citas detectadas",
    "✅ Verificación",
    "📊 Reporte",
])


# ═══════════════════════════════════════════════════════════════════════
# PESTAÑA 1 — CARGA Y PROCESAMIENTO DEL DOCUMENTO
# ═══════════════════════════════════════════════════════════════════════

with tab_doc:
    st.subheader("Cargar documento jurídico")
    st.caption("Formatos soportados: PDF, DOCX, TXT")

    archivo = st.file_uploader(
        "Seleccione el documento a analizar",
        type=["pdf", "docx", "txt"],
        help="El archivo se procesa exclusivamente en memoria. No se almacena ni transmite.",
    )

    if archivo is not None:
        with st.spinner("📖 Extrayendo texto del documento..."):
            try:
                bytes_archivo = archivo.read()
                texto_crudo = extraer_texto(bytes_archivo, archivo.name)
                texto_limpio = limpiar_texto(texto_crudo)
                st.session_state.nombre_archivo = archivo.name

                # Anonimización
                if anonimizar:
                    texto_procesado, registro = anonimizar_texto(texto_limpio)
                    st.session_state.texto_anonimizado = texto_procesado
                    st.session_state.registro_anonimizacion = registro
                else:
                    texto_procesado = texto_limpio
                    st.session_state.texto_anonimizado = texto_procesado
                    st.session_state.registro_anonimizacion = {}

                # Guardar para mostrar (primeras 3000 chars)
                st.session_state.texto_original_display = texto_procesado[:3000]

                # Extraer citas según filtros activos
                citas_extraidas = extraer_citas(texto_procesado)

                # Aplicar filtros de tipo
                tipos_activos = []
                if filtro_normas:
                    tipos_activos.append("norma")
                if filtro_cc:
                    tipos_activos.append("corte_constitucional")
                if filtro_csj:
                    tipos_activos.append("corte_suprema")
                if filtro_ce:
                    tipos_activos.append("consejo_estado")
                if filtro_doctrina:
                    tipos_activos.append("doctrina")

                st.session_state.citas = [c for c in citas_extraidas if c.tipo in tipos_activos]
                st.session_state.citas_verificadas = False

                st.success(
                    f"✅ Documento cargado: **{archivo.name}** — "
                    f"{len(texto_procesado):,} caracteres · "
                    f"**{len(st.session_state.citas)}** cita(s) detectada(s)"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el documento: {str(e)}")

    # Vista previa del texto
    if st.session_state.texto_original_display:
        st.markdown("### 📝 Vista previa del texto procesado")

        # Resumen de anonimización
        if st.session_state.registro_anonimizacion:
            st.info(resumen_anonimizacion(st.session_state.registro_anonimizacion))
        elif anonimizar:
            st.success("✅ No se detectaron datos personales identificables.")

        with st.expander("Ver primeros 3.000 caracteres del documento", expanded=False):
            st.text(st.session_state.texto_original_display)
            if len(st.session_state.texto_anonimizado) > 3000:
                st.caption(f"… y {len(st.session_state.texto_anonimizado) - 3000:,} caracteres más.")

    else:
        st.info("👆 Cargue un documento para comenzar el análisis.")


# ═══════════════════════════════════════════════════════════════════════
# PESTAÑA 2 — CITAS DETECTADAS
# ═══════════════════════════════════════════════════════════════════════

with tab_citas:
    if not st.session_state.citas:
        st.info("Cargue un documento en la pestaña **📄 Documento** para ver las citas detectadas.")
    else:
        citas = st.session_state.citas
        grupos = agrupar_por_tipo(citas)

        st.subheader(f"Citas detectadas: {len(citas)} en total")

        # Resumen por tipo
        col1, col2, col3, col4, col5 = st.columns(5)
        conteos = {tipo: len(lista) for tipo, lista in grupos.items()}
        for col, (tipo, icono) in zip(
            [col1, col2, col3, col4, col5],
            [("norma", "📜"), ("corte_constitucional", "⚖️"),
             ("corte_suprema", "🏛️"), ("consejo_estado", "🏢"), ("doctrina", "📚")]
        ):
            with col:
                st.metric(
                    label=f"{icono} {ETIQUETAS_TIPO_CORTO.get(tipo, tipo)}",
                    value=conteos.get(tipo, 0)
                )

        st.markdown("---")

        # Mostrar por grupo
        for tipo, lista in grupos.items():
            if lista:
                with st.expander(
                    f"{ETIQUETAS_TIPO.get(tipo, tipo)} — {len(lista)} cita(s)",
                    expanded=True
                ):
                    df_grupo = pd.DataFrame([{
                        "Subtipo": c.subtipo,
                        "Texto en documento": c.texto_original,
                        "Referencia normalizada": c.referencia,
                    } for c in lista])
                    st.dataframe(df_grupo, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════
# PESTAÑA 3 — VERIFICACIÓN
# ═══════════════════════════════════════════════════════════════════════

with tab_verificacion:
    if not st.session_state.citas:
        st.info("Cargue un documento y detecte citas antes de verificar.")
    else:
        st.subheader("Verificación en fuentes oficiales")

        # Advertencia si pocas fuentes activas
        fuentes_seleccionadas = [k for k, v in fuentes_activas.items() if v]
        if not fuentes_seleccionadas:
            st.error("⚠️ No hay fuentes de verificación activas. Active al menos una en la barra lateral.")
        else:
            st.caption(
                f"Fuentes activas: {', '.join(fuentes_seleccionadas)} · "
                f"{len(st.session_state.citas)} cita(s) a verificar · "
                "Se respeta un retardo entre peticiones para no saturar los servidores."
            )

            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                iniciar = st.button(
                    "🚀 Iniciar verificación",
                    type="primary",
                    disabled=st.session_state.citas_verificadas,
                )
            with col_btn2:
                if st.session_state.citas_verificadas:
                    st.success("✅ Verificación completada.")
                    if st.button("🔄 Volver a verificar"):
                        for c in st.session_state.citas:
                            c.estado = "pendiente"
                            c.fuente = ""
                            c.enlace = ""
                        st.session_state.citas_verificadas = False
                        st.rerun()

            if iniciar:
                citas = st.session_state.citas
                total = len(citas)
                barra = st.progress(0, text="Iniciando verificación…")
                contenedor_estado = st.empty()

                def actualizar_progreso(i, total, cita):
                    porcentaje = int((i / total) * 100)
                    barra.progress(
                        porcentaje / 100,
                        text=f"Verificando ({i+1}/{total}): {cita.referencia}"
                    )
                    contenedor_estado.info(
                        f"🔍 Consultando: **{cita.referencia}** en {cita.tipo.replace('_', ' ')}"
                    )

                try:
                    verificar_todas(citas, fuentes_activas, callback_progreso=actualizar_progreso)
                    barra.progress(1.0, text="✅ Verificación completada")
                    contenedor_estado.empty()
                    st.session_state.citas_verificadas = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error durante la verificación: {str(e)}")

        # Resultados
        if st.session_state.citas_verificadas:
            citas = st.session_state.citas
            df = citas_a_dataframe(citas)

            # Estadísticas rápidas
            stats = calcular_estadisticas(citas)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total citas", stats["total"])
            c2.metric("✅ Encontradas", stats["encontradas"])
            c3.metric("❌ No encontradas", stats["no_encontradas"])
            c4.metric("⚠️ No verificables", stats["no_verificables"])

            st.markdown("---")

            # Filtro rápido por estado
            estados_disponibles = ["Todos"] + list(
                {ETIQUETAS_ESTADO.get(c.estado, c.estado) for c in citas}
            )
            estado_filtro = st.selectbox("Filtrar por estado:", estados_disponibles)

            df_mostrar = df if estado_filtro == "Todos" else df[df["Estado"] == estado_filtro]

            # Aplicar colores a la tabla
            def colorear_estado(val):
                if "✅" in str(val):
                    return "background-color: #c6efce; color: #1a7a4a; font-weight: 600"
                elif "❌" in str(val):
                    return "background-color: #ffc7ce; color: #c0392b; font-weight: 600"
                elif "⚠️" in str(val):
                    return "background-color: #ffeb9c; color: #7f5a00; font-weight: 600"
                return ""

            st.dataframe(
                df_mostrar.style.applymap(colorear_estado, subset=["Estado"]),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Enlace": st.column_config.LinkColumn("Enlace", display_text="🔗 Abrir"),
                },
            )

            # Advertencia si hay no verificables
            if stats["no_verificables"] > 0:
                st.warning(
                    f"⚠️ {stats['no_verificables']} cita(s) no pudieron verificarse por "
                    "falta de respuesta de los servidores. Se recomienda consultarlas manualmente."
                )


# ═══════════════════════════════════════════════════════════════════════
# PESTAÑA 4 — REPORTE
# ═══════════════════════════════════════════════════════════════════════

with tab_reporte:
    if not st.session_state.citas:
        st.info("Cargue y analice un documento para generar el reporte.")
    elif not st.session_state.citas_verificadas:
        st.info("Complete la verificación en la pestaña **✅ Verificación** para generar el reporte.")
    else:
        citas = st.session_state.citas
        stats = calcular_estadisticas(citas)

        st.subheader("📊 Resumen del análisis")

        # Métricas principales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metrica-card verde">
                <strong>✅ Tasa de validez</strong><br>
                <span style="font-size:2rem;color:#1a7a4a;font-weight:700">{stats['pct_validas']}%</span><br>
                <small>{stats['encontradas']} de {stats['total']} citas encontradas</small>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metrica-card rojo">
                <strong>❌ No encontradas</strong><br>
                <span style="font-size:2rem;color:#c0392b;font-weight:700">{stats['no_encontradas']}</span><br>
                <small>Requieren revisión manual</small>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metrica-card amarillo">
                <strong>⚠️ No verificables</strong><br>
                <span style="font-size:2rem;color:#b7860b;font-weight:700">{stats['no_verificables']}</span><br>
                <small>Error de red o sin fuente</small>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Distribución por tipo
        st.markdown("### Distribución por tipo de cita")
        if stats["por_tipo"]:
            df_tipos = pd.DataFrame([
                {"Tipo": tipo, "Total": datos.get("total", 0)}
                for tipo, datos in stats["por_tipo"].items()
            ])
            st.bar_chart(df_tipos.set_index("Tipo"))

        st.markdown("---")

        # Aviso sobre IA responsable antes de descarga
        st.markdown("""
        <div class="aviso-legal">
        ⚠️ <strong>Aviso de IA Responsable</strong>: Este reporte es de carácter orientativo. 
        La verificación automática puede presentar falsos positivos o negativos por cambios en los 
        sitios web, indisponibilidad de servidores o limitaciones técnicas de extracción. 
        <strong>Toda cita debe ser confirmada por el profesional jurídico responsable</strong> antes 
        de utilizarse en documentos oficiales. El sistema no toma decisiones jurídicas autónomas.
        </div>
        """, unsafe_allow_html=True)

        # Descarga Excel
        try:
            bytes_excel = exportar_excel(citas, st.session_state.nombre_archivo)
            st.download_button(
                label="📥 Descargar reporte en Excel (.xlsx)",
                data=bytes_excel,
                file_name=f"reporte_citas_{st.session_state.nombre_archivo.rsplit('.', 1)[0]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )
        except Exception as e:
            st.error(f"Error al generar el Excel: {str(e)}")

        # Tabla final completa
        st.markdown("### Tabla completa de resultados")
        df_final = citas_a_dataframe(citas)

        def colorear_estado(val):
            if "✅" in str(val):
                return "background-color: #c6efce; color: #1a7a4a; font-weight: 600"
            elif "❌" in str(val):
                return "background-color: #ffc7ce; color: #c0392b; font-weight: 600"
            elif "⚠️" in str(val):
                return "background-color: #ffeb9c; color: #7f5a00; font-weight: 600"
            return ""

        st.dataframe(
            df_final.style.applymap(colorear_estado, subset=["Estado"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Enlace": st.column_config.LinkColumn("Enlace", display_text="🔗 Abrir"),
            },
        )
