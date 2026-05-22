# app.py — Verificador de Citas Jurídicas Colombianas
# Cumplimiento: Ley 1581/2012 (Habeas Data), IA Responsable.

import streamlit as st
import pandas as pd

from anonimizador import anonimizar_texto, generar_advertencia_habeas_data, resumen_anonimizacion
from extractor import extraer_citas, agrupar_por_tipo, ETIQUETAS_TIPO, Cita
from verificador import verificar_cita, verificar_todas
from utils import (
    extraer_texto, limpiar_texto, exportar_excel,
    calcular_estadisticas, ETIQUETAS_TIPO_CORTO,
)

# ── Página ────────────────────────────────────────────────────────────────────
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
.header-box h1 { font-family:'Playfair Display',serif; color:#e8d9b5;
                 font-size:1.9rem; margin:0 0 .2rem; }
.header-box p  { color:#a8c4e0; font-size:.9rem; margin:0; }
.badge { display:inline-block; background:#e8f4f8; color:#1b5c7a;
         border:1px solid #a8cfe0; border-radius:20px;
         padding:.15rem .7rem; font-size:.75rem; font-weight:600; margin-top:.4rem; }
.aviso { background:#fffbf0; border:1px solid #d4a017; border-radius:8px;
         padding:.9rem; font-size:.85rem; color:#5a4a00; margin-bottom:.8rem; }
.link-box { background:#f0f4f8; border-radius:8px; padding:.7rem 1rem;
            margin:.3rem 0; font-size:.85rem; }
.link-box a { color:#1b3a5c; font-weight:600; text-decoration:none; }
.link-box a:hover { text-decoration:underline; }
section[data-testid="stSidebar"] { background:#0d1b2a; }
section[data-testid="stSidebar"] * { color:#d0dde8 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
  <h1>⚖️ Verificador de Citas Jurídicas Colombianas</h1>
  <p>Detección de normas, jurisprudencia y doctrina · Enlaces directos para verificación manual en SUIN-Juriscol y fuentes oficiales.</p>
  <span class="badge">🤖 IA Responsable · Habeas Data · Uso orientativo</span>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    st.markdown("---")
    st.markdown("### 🔎 Tipos de cita a detectar")
    filtro_normas   = st.checkbox("📜 Normas legales",            value=True)
    filtro_cc       = st.checkbox("⚖️ Corte Constitucional",      value=True)
    filtro_csj      = st.checkbox("🏛️ Corte Suprema de Justicia", value=True)
    filtro_ce       = st.checkbox("🏢 Consejo de Estado",         value=True)
    filtro_doctrina = st.checkbox("📚 Doctrina (ISBN / DOI)",     value=True)

    st.markdown("---")
    st.markdown("### 🔒 Privacidad")
    hacer_anonimizar = st.toggle("Anonimizar datos personales", value=True,
        help="Elimina nombres, cédulas, teléfonos, etc. antes del análisis (Ley 1581/2012)")

    st.markdown("---")
    st.info(
        "ℹ️ **Sobre la verificación**\n\n"
        "Por restricciones de red en servidores cloud, la app genera **enlaces directos** "
        "para que usted consulte cada cita en SUIN-Juriscol, Google y las relatorías oficiales. "
        "Abra el enlace con un clic desde su navegador.",
        icon=None,
    )
    st.caption("Herramienta orientativa. No reemplaza el criterio del profesional jurídico.")

# ── Aviso Habeas Data ─────────────────────────────────────────────────────────
with st.expander("⚖️ Aviso legal — Habeas Data e IA Responsable", expanded=False):
    st.markdown(generar_advertencia_habeas_data())
st.markdown("---")

# ── Session state ─────────────────────────────────────────────────────────────
for key, val in {
    "citas_dicts":  [],
    "enlaces_generados": False,
    "nombre_archivo": "",
    "texto_display": "",
    "registro_anon": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📄 Documento", "🔍 Citas detectadas", "🔗 Enlaces de verificación", "📊 Reporte"
])

# ══════════════════════════════════════════════════════
# TAB 1 — DOCUMENTO
# ══════════════════════════════════════════════════════
with tab1:
    st.subheader("Cargar documento jurídico")
    st.caption("Formatos: PDF · DOCX · TXT")

    archivo = st.file_uploader(
        "Seleccione el documento",
        type=["pdf", "docx", "txt"],
        help="El archivo se procesa solo en memoria. No se almacena ni transmite.",
    )

    if archivo is not None:
        with st.spinner("📖 Extrayendo y procesando el documento…"):
            try:
                raw   = archivo.read()
                texto = limpiar_texto(extraer_texto(raw, archivo.name))
                st.session_state.nombre_archivo = archivo.name

                if hacer_anonimizar:
                    texto, registro = anonimizar_texto(texto)
                    st.session_state.registro_anon = registro
                else:
                    st.session_state.registro_anon = {}

                st.session_state.texto_display = texto[:3000]

                tipos_ok = []
                if filtro_normas:   tipos_ok.append("norma")
                if filtro_cc:       tipos_ok.append("corte_constitucional")
                if filtro_csj:      tipos_ok.append("corte_suprema")
                if filtro_ce:       tipos_ok.append("consejo_estado")
                if filtro_doctrina: tipos_ok.append("doctrina")

                citas = [c for c in extraer_citas(texto) if c.tipo in tipos_ok]

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
                st.session_state.enlaces_generados = False

                st.success(
                    f"✅ **{archivo.name}** cargado — "
                    f"{len(texto):,} caracteres · "
                    f"**{len(citas)}** cita(s) detectada(s)"
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

# ══════════════════════════════════════════════════════
# TAB 2 — CITAS DETECTADAS
# ══════════════════════════════════════════════════════
with tab2:
    citas_dicts = st.session_state.citas_dicts
    if not citas_dicts:
        st.info("Cargue un documento en **📄 Documento** para ver las citas detectadas.")
    else:
        st.subheader(f"Citas detectadas: {len(citas_dicts)}")

        conteo = {}
        for d in citas_dicts:
            conteo[d["tipo"]] = conteo.get(d["tipo"], 0) + 1

        cols = st.columns(5)
        for col, (tipo, icono) in zip(cols, [
            ("norma","📜"),("corte_constitucional","⚖️"),
            ("corte_suprema","🏛️"),("consejo_estado","🏢"),("doctrina","📚")
        ]):
            col.metric(f"{icono} {ETIQUETAS_TIPO_CORTO.get(tipo, tipo)}", conteo.get(tipo, 0))

        st.markdown("---")
        grupos = {}
        for d in citas_dicts:
            grupos.setdefault(d["tipo"], []).append(d)

        for tipo, lista in grupos.items():
            with st.expander(f"{ETIQUETAS_TIPO.get(tipo, tipo)} — {len(lista)} cita(s)", expanded=True):
                st.dataframe(
                    pd.DataFrame([{
                        "Subtipo": d["subtipo"],
                        "Texto en documento": d["texto_original"],
                        "Referencia normalizada": d["referencia"],
                    } for d in lista]),
                    use_container_width=True, hide_index=True,
                )

# ══════════════════════════════════════════════════════
# TAB 3 — ENLACES DE VERIFICACIÓN
# ══════════════════════════════════════════════════════
with tab3:
    citas_dicts = st.session_state.citas_dicts

    if not citas_dicts:
        st.info("Cargue un documento en **📄 Documento** para generar los enlaces.")
    else:
        st.subheader("🔗 Enlaces de verificación manual")
        st.markdown(
            "La app genera enlaces directos a **SUIN-Juriscol** (via Google), "
            "las **relatorías oficiales** de cada corte y buscadores generales. "
            "Haga clic en cualquier enlace para abrirlo en su navegador y verificar la cita."
        )

        ya_generados = st.session_state.enlaces_generados

        col_a, col_b = st.columns([1, 4])
        with col_a:
            generar = st.button(
                "🔗 Generar enlaces",
                type="primary",
                disabled=ya_generados,
            )
        with col_b:
            if ya_generados:
                st.success("✅ Enlaces generados — consulte cada cita en su navegador.")
            if ya_generados and st.button("🔄 Regenerar"):
                for d in st.session_state.citas_dicts:
                    d["estado"] = "pendiente"; d["fuente"] = ""; d["enlace"] = ""
                st.session_state.enlaces_generados = False
                st.rerun()

        # ── Proceso de generación (instantáneo, sin red) ──────────────────────
        if generar:
            barra = st.progress(0, text="Generando enlaces…")
            total = len(st.session_state.citas_dicts)

            for i, d in enumerate(st.session_state.citas_dicts):
                barra.progress((i + 1) / total, text=f"Procesando {i+1}/{total}: {d['referencia']}")
                cita_obj = Cita(
                    tipo=d["tipo"], subtipo=d["subtipo"],
                    texto_original=d["texto_original"],
                    referencia=d["referencia"],
                )
                verificar_cita(cita_obj)
                d["estado"] = cita_obj.estado
                d["fuente"] = cita_obj.fuente
                d["enlace"] = cita_obj.enlace

            barra.progress(1.0, text="✅ Completado")
            st.session_state.enlaces_generados = True

        # ── Mostrar enlaces por cita ───────────────────────────────────────────
        con_enlaces = [d for d in st.session_state.citas_dicts if d["estado"] == "generado"]

        if con_enlaces:
            st.markdown("---")

            # Filtro por tipo
            tipos_presentes = sorted({d["tipo"] for d in con_enlaces})
            opciones_filtro = ["Todos los tipos"] + [
                ETIQUETAS_TIPO_CORTO.get(t, t) for t in tipos_presentes
            ]
            filtro_tipo = st.selectbox("Filtrar por tipo:", opciones_filtro)

            if filtro_tipo != "Todos los tipos":
                tipo_filtrado = next(
                    (t for t in tipos_presentes if ETIQUETAS_TIPO_CORTO.get(t, t) == filtro_tipo),
                    None
                )
                mostrar = [d for d in con_enlaces if d["tipo"] == tipo_filtrado]
            else:
                mostrar = con_enlaces

            st.caption(f"Mostrando {len(mostrar)} cita(s)")

            for d in mostrar:
                icono = {
                    "norma": "📜", "corte_constitucional": "⚖️",
                    "corte_suprema": "🏛️", "consejo_estado": "🏢", "doctrina": "📚"
                }.get(d["tipo"], "📄")

                with st.expander(
                    f"{icono} **{d['referencia']}** · {ETIQUETAS_TIPO_CORTO.get(d['tipo'], d['tipo'])} · {d['subtipo']}",
                    expanded=False,
                ):
                    st.caption(f"Texto original en el documento: *{d['texto_original']}*")
                    st.markdown("**🔗 Enlaces para verificar esta cita:**")

                    # Parsear los pares "Etiqueta: URL" del campo fuente
                    pares = d["fuente"].split(" | ")
                    for par in pares:
                        if ": http" in par:
                            idx   = par.index(": http")
                            label = par[:idx].strip()
                            url   = par[idx+2:].strip()
                            st.markdown(
                                f'<div class="link-box">'
                                f'{label}: <a href="{url}" target="_blank">{url}</a>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

            # ── Tabla resumen compacta ────────────────────────────────────────
            st.markdown("---")
            st.markdown("### Tabla resumen")
            st.caption("El enlace principal de cada fila abre la búsqueda en SUIN-Juriscol via Google.")

            df = pd.DataFrame([{
                "Tipo":        ETIQUETAS_TIPO_CORTO.get(d["tipo"], d["tipo"]),
                "Subtipo":     d["subtipo"],
                "Referencia":  d["referencia"],
                "Enlace SUIN (Google)": d["enlace"],
            } for d in mostrar])

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Enlace SUIN (Google)": st.column_config.LinkColumn(
                        "Enlace SUIN (Google)",
                        display_text="🔍 Buscar en SUIN",
                    ),
                },
            )

# ══════════════════════════════════════════════════════
# TAB 4 — REPORTE
# ══════════════════════════════════════════════════════
with tab4:
    citas_dicts  = st.session_state.citas_dicts
    con_enlaces  = [d for d in citas_dicts if d["estado"] == "generado"]

    if not citas_dicts:
        st.info("Cargue un documento para generar el reporte.")
    elif not con_enlaces:
        st.info("Genere los enlaces en **🔗 Enlaces de verificación** para activar el reporte.")
    else:
        citas_obj = [
            Cita(tipo=d["tipo"], subtipo=d["subtipo"],
              texto_original=d["texto_original"], referencia=d["referencia"],
              estado=d["estado"], fuente=d["fuente"], enlace=d["enlace"])
            for d in citas_dicts
        ]

        total = len(citas_obj)
        st.subheader("📊 Resumen del análisis")

        # Distribución por tipo
        conteo_tipo = {}
        for d in citas_dicts:
            etiq = ETIQUETAS_TIPO_CORTO.get(d["tipo"], d["tipo"])
            conteo_tipo[etiq] = conteo_tipo.get(etiq, 0) + 1

        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Total de citas detectadas", total)
            for etiq, cnt in conteo_tipo.items():
                st.metric(etiq, cnt)
        with col2:
            if conteo_tipo:
                df_tipos = pd.DataFrame(
                    list(conteo_tipo.items()), columns=["Tipo", "Total"]
                )
                st.bar_chart(df_tipos.set_index("Tipo"))

        st.markdown("---")

        # Aviso IA responsable
        st.markdown("""
        <div class="aviso">
        ⚠️ <strong>Aviso de IA Responsable</strong>: Este reporte lista las citas detectadas
        automáticamente y los enlaces generados para su verificación manual. La detección
        puede tener falsos positivos o negativos según la redacción del documento.
        <strong>Toda cita debe ser confirmada por el profesional jurídico responsable</strong>
        antes de usarse en documentos oficiales. El sistema no toma decisiones jurídicas autónomas.
        </div>
        """, unsafe_allow_html=True)

        # Descarga Excel
        try:
            citas_export = [
                Cita(tipo=d["tipo"], subtipo=d["subtipo"],
                     texto_original=d["texto_original"], referencia=d["referencia"],
                     estado="no_verificable",
                     fuente="Ver enlaces en la app",
                     enlace=d["enlace"])
                for d in citas_dicts
            ]
            bytes_xl = exportar_excel(citas_export, st.session_state.nombre_archivo)
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

        # Tabla completa con todos los enlaces
        st.markdown("### Tabla completa de citas y enlaces")
        filas = []
        for d in citas_dicts:
            # Extraer primer enlace real (SUIN Google)
            enlace_principal = d.get("enlace", "")
            filas.append({
                "Tipo":       ETIQUETAS_TIPO_CORTO.get(d["tipo"], d["tipo"]),
                "Subtipo":    d["subtipo"],
                "Referencia": d["referencia"],
                "Enlace SUIN (Google)": enlace_principal,
            })

        df_final = pd.DataFrame(filas)
        st.dataframe(
            df_final,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Enlace SUIN (Google)": st.column_config.LinkColumn(
                    "Enlace SUIN (Google)",
                    display_text="🔍 Buscar en SUIN",
                ),
            },
        )
