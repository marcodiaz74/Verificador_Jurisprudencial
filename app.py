# app.py — Verificador de Citas Jurídicas Colombianas
# Cumplimiento: Ley 1581/2012 (Habeas Data), IA Responsable.

import streamlit as st
import pandas as pd
import time
import requests

from anonimizador import anonimizar_texto, generar_advertencia_habeas_data, resumen_anonimizacion
from extractor import extraer_citas, agrupar_por_tipo, ETIQUETAS_TIPO
from verificador import verificar_cita, _crear_sesion
from utils import (
    extraer_texto, limpiar_texto, citas_a_dataframe,
    exportar_excel, calcular_estadisticas,
    ETIQUETAS_ESTADO, ETIQUETAS_TIPO_CORTO,
)

# ── Página ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Verificador de Citas Jurídicas · Colombia",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Source+Sans+3:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'Source Sans 3', sans-serif; }
.header-box {
    background: linear-gradient(135deg,#0d1b2a,#1b3a5c,#2a5c8a);
    padding: 1.8rem 2.2rem 1.4rem; border-radius: 12px;
    margin-bottom: 1.4rem; box-shadow: 0 4px 20px rgba(13,27,42,.35);
}
.header-box h1 { font-family:'Playfair Display',serif; color:#e8d9b5; font-size:1.9rem; margin:0 0 .2rem; }
.header-box p  { color:#a8c4e0; font-size:.9rem; margin:0; }
.badge { display:inline-block; background:#e8f4f8; color:#1b5c7a;
         border:1px solid #a8cfe0; border-radius:20px;
         padding:.15rem .7rem; font-size:.75rem; font-weight:600; margin-top:.4rem; }
.aviso { background:#fffbf0; border:1px solid #d4a017; border-radius:8px;
         padding:.9rem; font-size:.85rem; color:#5a4a00; margin-bottom:.8rem; }
section[data-testid="stSidebar"] { background:#0d1b2a; }
section[data-testid="stSidebar"] * { color:#d0dde8 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
  <h1>⚖️ Verificador de Citas Jurídicas Colombianas</h1>
  <p>Detección y verificación automática de normas, jurisprudencia y doctrina en documentos legales.</p>
  <span class="badge">🤖 IA Responsable · Habeas Data · Uso orientativo</span>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    st.markdown("---")
    st.markdown("### 🔎 Tipos de cita")
    filtro_normas   = st.checkbox("📜 Normas legales",           value=True)
    filtro_cc       = st.checkbox("⚖️ Corte Constitucional",     value=True)
    filtro_csj      = st.checkbox("🏛️ Corte Suprema de Justicia",value=True)
    filtro_ce       = st.checkbox("🏢 Consejo de Estado",        value=True)
    filtro_doctrina = st.checkbox("📚 Doctrina (ISBN / DOI)",    value=True)

    st.markdown("---")
    st.markdown("### 🌐 Fuentes de verificación")
    f_suin   = st.checkbox("SUIN-Juriscol",       value=True)
    f_fp     = st.checkbox("Función Pública",      value=True)
    f_cc     = st.checkbox("Corte Constitucional", value=True)
    f_csj    = st.checkbox("Corte Suprema",        value=True)
    f_ce     = st.checkbox("Consejo de Estado",    value=True)

    fuentes_activas = {
        "suin": f_suin, "funcion_publica": f_fp,
        "corte_constitucional": f_cc, "corte_suprema": f_csj, "consejo_estado": f_ce,
    }

    st.markdown("---")
    st.markdown("### 🔒 Privacidad")
    hacer_anonimizar = st.toggle("Anonimizar datos personales", value=True,
        help="Elimina nombres, cédulas, teléfonos, etc. (recomendado)")

    st.markdown("---")
    st.caption("Herramienta orientativa. No reemplaza el criterio del profesional jurídico. Ley 1581/2012.")

# ── Aviso Habeas Data ──────────────────────────────────────────────────
with st.expander("⚖️ Aviso legal — Habeas Data e IA Responsable", expanded=False):
    st.markdown(generar_advertencia_habeas_data())
st.markdown("---")

# ── Session state ──────────────────────────────────────────────────────
# Guardamos las citas como lista de dicts (JSON-serializable) para que
# Streamlit no pierda el estado entre reruns.
for key, val in {
    "citas_dicts": [],          # lista de dicts con todos los campos de Cita
    "verificacion_completa": False,
    "nombre_archivo": "",
    "texto_display": "",
    "registro_anon": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Tabs ───────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📄 Documento", "🔍 Citas detectadas", "✅ Verificación", "📊 Reporte"
])

# ════════════════════════════════════════════
# TAB 1 — DOCUMENTO
# ════════════════════════════════════════════
with tab1:
    st.subheader("Cargar documento jurídico")
    st.caption("Formatos: PDF · DOCX · TXT")

    archivo = st.file_uploader(
        "Seleccione el documento",
        type=["pdf", "docx", "txt"],
        help="Procesado solo en memoria. No se almacena ni transmite.",
    )

    if archivo is not None:
        with st.spinner("📖 Extrayendo y procesando el documento…"):
            try:
                raw = archivo.read()
                texto = limpiar_texto(extraer_texto(raw, archivo.name))
                st.session_state.nombre_archivo = archivo.name

                if hacer_anonimizar:
                    texto, registro = anonimizar_texto(texto)
                    st.session_state.registro_anon = registro
                else:
                    st.session_state.registro_anon = {}

                st.session_state.texto_display = texto[:3000]

                # Filtros activos
                tipos_ok = []
                if filtro_normas:   tipos_ok.append("norma")
                if filtro_cc:       tipos_ok.append("corte_constitucional")
                if filtro_csj:      tipos_ok.append("corte_suprema")
                if filtro_ce:       tipos_ok.append("consejo_estado")
                if filtro_doctrina: tipos_ok.append("doctrina")

                citas = [c for c in extraer_citas(texto) if c.tipo in tipos_ok]

                # Convertir a dicts para guardar en session_state de forma segura
                st.session_state.citas_dicts = [
                    {
                        "tipo": c.tipo, "subtipo": c.subtipo,
                        "texto_original": c.texto_original,
                        "referencia": c.referencia,
                        "estado": "pendiente",
                        "fuente": "", "enlace": "",
                    }
                    for c in citas
                ]
                st.session_state.verificacion_completa = False

                st.success(
                    f"✅ **{archivo.name}** cargado — "
                    f"{len(texto):,} caracteres · **{len(citas)}** cita(s) detectada(s)"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el documento: {e}")

    if st.session_state.texto_display:
        if st.session_state.registro_anon:
            st.info(resumen_anonimizacion(st.session_state.registro_anon))
        elif hacer_anonimizar:
            st.success("✅ No se detectaron datos personales identificables.")

        with st.expander("Ver primeros 3.000 caracteres del texto procesado"):
            st.text(st.session_state.texto_display)
    else:
        st.info("👆 Cargue un documento para comenzar el análisis.")

# ════════════════════════════════════════════
# TAB 2 — CITAS DETECTADAS
# ════════════════════════════════════════════
with tab2:
    citas_dicts = st.session_state.citas_dicts
    if not citas_dicts:
        st.info("Cargue un documento en **📄 Documento** para ver las citas detectadas.")
    else:
        st.subheader(f"Citas detectadas: {len(citas_dicts)}")

        # Conteo por tipo
        conteo = {}
        for d in citas_dicts:
            conteo[d["tipo"]] = conteo.get(d["tipo"], 0) + 1

        cols = st.columns(5)
        for col, (tipo, icono) in zip(cols, [
            ("norma","📜"),("corte_constitucional","⚖️"),
            ("corte_suprema","🏛️"),("consejo_estado","🏢"),("doctrina","📚")
        ]):
            col.metric(f"{icono} {ETIQUETAS_TIPO_CORTO.get(tipo,tipo)}", conteo.get(tipo,0))

        st.markdown("---")

        # Tabla por tipo
        grupos = {}
        for d in citas_dicts:
            grupos.setdefault(d["tipo"], []).append(d)

        for tipo, lista in grupos.items():
            with st.expander(f"{ETIQUETAS_TIPO.get(tipo,tipo)} — {len(lista)} cita(s)", expanded=True):
                st.dataframe(
                    pd.DataFrame([{
                        "Subtipo": d["subtipo"],
                        "Texto en documento": d["texto_original"],
                        "Referencia normalizada": d["referencia"],
                    } for d in lista]),
                    use_container_width=True, hide_index=True,
                )

# ════════════════════════════════════════════
# TAB 3 — VERIFICACIÓN
# ════════════════════════════════════════════
with tab3:
    citas_dicts = st.session_state.citas_dicts

    if not citas_dicts:
        st.info("Cargue un documento y detecte citas antes de verificar.")
    else:
        st.subheader("Verificación en fuentes oficiales")

        fuentes_sel = [k for k, v in fuentes_activas.items() if v]
        if not fuentes_sel:
            st.error("Active al menos una fuente de verificación en la barra lateral.")
        else:
            total_citas = len(citas_dicts)
            ya_completa = st.session_state.verificacion_completa

            col_a, col_b = st.columns([1, 4])
            with col_a:
                iniciar = st.button(
                    "🚀 Iniciar verificación", type="primary",
                    disabled=ya_completa,
                )
            with col_b:
                if ya_completa:
                    st.success("✅ Verificación completada — vea el **📊 Reporte**.")
                if ya_completa and st.button("🔄 Volver a verificar"):
                    for d in st.session_state.citas_dicts:
                        d["estado"] = "pendiente"; d["fuente"] = ""; d["enlace"] = ""
                    st.session_state.verificacion_completa = False
                    st.rerun()

            # ── Proceso principal — SIN st.rerun() dentro del loop ──
            if iniciar:
                barra      = st.progress(0, text="Iniciando…")
                estado_txt = st.empty()
                sesion     = _crear_sesion()
                errores    = []

                for i, d in enumerate(st.session_state.citas_dicts):
                    pct = i / total_citas
                    barra.progress(pct, text=f"Verificando {i+1}/{total_citas}: {d['referencia']}")
                    estado_txt.info(f"🔍 **{d['referencia']}** · {d['tipo'].replace('_',' ')}")

                    # Reconstruir objeto Cita desde el dict
                    from extractor import Cita
                    cita_obj = Cita(
                        tipo=d["tipo"], subtipo=d["subtipo"],
                        texto_original=d["texto_original"],
                        referencia=d["referencia"],
                    )

                    try:
                        verificar_cita(cita_obj, fuentes_activas, sesion)
                        d["estado"] = cita_obj.estado
                        d["fuente"] = cita_obj.fuente
                        d["enlace"] = cita_obj.enlace
                    except Exception as e:
                        d["estado"] = "no_verificable"
                        d["fuente"] = f"Error: {str(e)[:80]}"
                        d["enlace"] = ""
                        errores.append(d["referencia"])

                barra.progress(1.0, text="✅ Completado")
                estado_txt.empty()

                # Marcar como completo — SIN rerun para no perder el estado
                st.session_state.verificacion_completa = True

                if errores:
                    st.warning(f"⚠️ {len(errores)} cita(s) con error de red — quedan como 'No verificable'.")
                else:
                    st.success("✅ Todas las citas fueron consultadas. Vea el **📊 Reporte**.")

        # ── Tabla de resultados (visible si hay estados procesados) ──
        con_estado = [d for d in st.session_state.citas_dicts if d["estado"] != "pendiente"]
        if con_estado:
            from extractor import Cita as C2
            citas_obj = [
                C2(tipo=d["tipo"], subtipo=d["subtipo"],
                   texto_original=d["texto_original"], referencia=d["referencia"],
                   estado=d["estado"], fuente=d["fuente"], enlace=d["enlace"])
                for d in st.session_state.citas_dicts
            ]
            stats = calcular_estadisticas(citas_obj)

            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total",             stats["total"])
            c2.metric("✅ Encontradas",    stats["encontradas"])
            c3.metric("❌ No encontradas", stats["no_encontradas"])
            c4.metric("⚠️ No verificables",stats["no_verificables"])

            df = citas_a_dataframe(citas_obj)
            estados_disp = ["Todos"] + sorted({
                ETIQUETAS_ESTADO.get(d["estado"], d["estado"]) for d in con_estado
            })
            filtro_est = st.selectbox("Filtrar por estado:", estados_disp)
            df_m = df if filtro_est == "Todos" else df[df["Estado"] == filtro_est]

            def colorear(val):
                if "✅" in str(val): return "background-color:#c6efce;color:#1a7a4a;font-weight:600"
                if "❌" in str(val): return "background-color:#ffc7ce;color:#c0392b;font-weight:600"
                if "⚠️" in str(val): return "background-color:#ffeb9c;color:#7f5a00;font-weight:600"
                return ""

            st.dataframe(
                df_m.style.map(colorear, subset=["Estado"]),
                use_container_width=True, hide_index=True,
                column_config={"Enlace": st.column_config.LinkColumn("Enlace", display_text="🔗 Abrir")},
            )

# ════════════════════════════════════════════
# TAB 4 — REPORTE
# ════════════════════════════════════════════
with tab4:
    citas_dicts    = st.session_state.citas_dicts
    con_estado     = [d for d in citas_dicts if d["estado"] != "pendiente"]

    if not citas_dicts:
        st.info("Cargue y analice un documento para generar el reporte.")
    elif not con_estado:
        st.info("Complete la verificación en **✅ Verificación** para generar el reporte.")
    else:
        from extractor import Cita as C3
        citas_obj = [
            C3(tipo=d["tipo"], subtipo=d["subtipo"],
               texto_original=d["texto_original"], referencia=d["referencia"],
               estado=d["estado"], fuente=d["fuente"], enlace=d["enlace"])
            for d in citas_dicts
        ]
        stats = calcular_estadisticas(citas_obj)

        st.subheader("📊 Resumen del análisis")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""<div style="background:#eafaf1;border-left:5px solid #1a7a4a;
                border-radius:8px;padding:1rem .9rem;margin-bottom:.6rem">
                <strong>✅ Tasa de validez</strong><br>
                <span style="font-size:2rem;color:#1a7a4a;font-weight:700">{stats['pct_validas']}%</span><br>
                <small>{stats['encontradas']} de {stats['total']} encontradas</small>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div style="background:#fdedec;border-left:5px solid #c0392b;
                border-radius:8px;padding:1rem .9rem;margin-bottom:.6rem">
                <strong>❌ No encontradas</strong><br>
                <span style="font-size:2rem;color:#c0392b;font-weight:700">{stats['no_encontradas']}</span><br>
                <small>Requieren revisión manual</small>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div style="background:#fef9e7;border-left:5px solid #d4a017;
                border-radius:8px;padding:1rem .9rem;margin-bottom:.6rem">
                <strong>⚠️ No verificables</strong><br>
                <span style="font-size:2rem;color:#b7860b;font-weight:700">{stats['no_verificables']}</span><br>
                <small>Error de red o sin fuente</small>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")

        if stats["por_tipo"]:
            st.markdown("### Distribución por tipo de cita")
            df_tipos = pd.DataFrame([
                {"Tipo": t, "Total": datos.get("total", 0)}
                for t, datos in stats["por_tipo"].items()
            ])
            st.bar_chart(df_tipos.set_index("Tipo"))

        st.markdown("---")
        st.markdown("""<div class="aviso">
            ⚠️ <strong>Aviso de IA Responsable</strong>: Este reporte es orientativo.
            La verificación automática puede presentar falsos positivos/negativos.
            <strong>Toda cita debe ser confirmada por el profesional jurídico</strong>
            antes de usarse en documentos oficiales. El sistema no toma decisiones autónomas.
        </div>""", unsafe_allow_html=True)

        # Botón de descarga Excel
        try:
            bytes_xl = exportar_excel(citas_obj, st.session_state.nombre_archivo)
            nombre_base = st.session_state.nombre_archivo.rsplit(".", 1)[0]
            st.download_button(
                label="📥 Descargar reporte en Excel (.xlsx)",
                data=bytes_xl,
                file_name=f"reporte_citas_{nombre_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )
        except Exception as e:
            st.error(f"Error al generar el Excel: {e}")

        # Tabla final completa
        st.markdown("### Tabla completa de resultados")
        df_final = citas_a_dataframe(citas_obj)

        def colorear2(val):
            if "✅" in str(val): return "background-color:#c6efce;color:#1a7a4a;font-weight:600"
            if "❌" in str(val): return "background-color:#ffc7ce;color:#c0392b;font-weight:600"
            if "⚠️" in str(val): return "background-color:#ffeb9c;color:#7f5a00;font-weight:600"
            return ""

        st.dataframe(
            df_final.style.map(colorear2, subset=["Estado"]),
            use_container_width=True, hide_index=True,
            column_config={"Enlace": st.column_config.LinkColumn("Enlace", display_text="🔗 Abrir")},
        )
