# ⚖️ Verificador de Citas Jurídicas Colombianas

Herramienta de análisis automatizado de citas normativas y jurisprudenciales en documentos
jurídicos colombianos (demandas, sentencias, conceptos, doctrina, etc.).

---

## 📋 ¿Qué hace esta aplicación?

1. **Carga documentos** en formato PDF, DOCX o TXT.
2. **Anonimiza automáticamente** los datos personales (nombres, cédulas, teléfonos, etc.)
   en cumplimiento de la **Ley 1581 de 2012 (Habeas Data)**.
3. **Detecta citas** de:
   - Normas: Leyes, Decretos, Resoluciones, Actos Legislativos, Circulares, Códigos.
   - Corte Constitucional: Sentencias T, C, SU y Autos A.
   - Corte Suprema de Justicia: SC, SL, SP y radicados.
   - Consejo de Estado: Radicados, Expedientes y Secciones.
   - Doctrina: ISBN y DOI.
4. **Verifica** cada cita en las fuentes oficiales colombianas.
5. **Genera un reporte** descargable en Excel (.xlsx).

> ⚠️ **Herramienta orientativa.** No reemplaza el criterio del profesional jurídico.
> Cumple con los principios de IA Responsable: transparencia, supervisión humana
> y minimización de datos.

---

## 🚀 Despliegue en Streamlit Community Cloud (sin instalar Python)

### Paso 1 — Crear cuenta en GitHub (si no tiene una)

1. Vaya a [https://github.com](https://github.com) y cree una cuenta gratuita.

### Paso 2 — Subir los archivos a un repositorio de GitHub

1. En GitHub, haga clic en **"New repository"** (botón verde).
2. Nombre el repositorio, por ejemplo: `verificador-juridico-colombia`.
3. Déjelo en **público** (Streamlit Cloud requiere repos públicos en el plan gratuito).
4. Haga clic en **"Create repository"**.
5. En la página del repositorio vacío, haga clic en **"uploading an existing file"**.
6. Arrastre y suelte todos los archivos del proyecto:
   - `app.py`
   - `anonimizador.py`
   - `extractor.py`
   - `verificador.py`
   - `utils.py`
   - `requirements.txt`
   - `README.md`
7. Escriba un mensaje de commit como `"Primera versión"` y haga clic en **"Commit changes"**.

### Paso 3 — Desplegar en Streamlit Community Cloud

1. Vaya a [https://streamlit.io/cloud](https://streamlit.io/cloud).
2. Haga clic en **"Sign up"** o **"Log in"** usando su cuenta de GitHub.
3. Haga clic en **"New app"**.
4. En **"Repository"**, seleccione `verificador-juridico-colombia`.
5. En **"Branch"**, deje `main`.
6. En **"Main file path"**, escriba `app.py`.
7. Haga clic en **"Deploy!"**.
8. Espere 2–4 minutos mientras Streamlit instala las dependencias del `requirements.txt`.
9. ✅ ¡La aplicación estará disponible en una URL pública como
   `https://[su-usuario]-verificador-juridico.streamlit.app`!

---

## 📁 Estructura del proyecto

```
verificador_juridico/
├── app.py              # Interfaz principal (Streamlit)
├── anonimizador.py     # Protección de datos personales (Habeas Data)
├── extractor.py        # Detección de citas con expresiones regulares
├── verificador.py      # Verificación en fuentes oficiales
├── utils.py            # Lectura de documentos y exportación a Excel
├── requirements.txt    # Dependencias Python
└── README.md           # Este archivo
```

---

## ⚖️ Marco legal y principios de IA responsable

| Norma / Principio | Aplicación en la herramienta |
|---|---|
| Ley 1581 de 2012 (Habeas Data) | Anonimización automática de datos personales antes del análisis |
| Ley 1266 de 2008 | No se procesan ni almacenan datos financieros |
| Decreto 1377 de 2013 | Minimización de datos: solo se usa lo necesario para verificar |
| Principio de transparencia (IA) | El usuario ve qué datos se anonimizaron y por qué |
| Principio de supervisión humana | Resultado es orientativo; el jurista toma la decisión final |
| No almacenamiento | Todo el procesamiento ocurre en memoria durante la sesión |

---

## 🔧 Fuentes oficiales consultadas

| Fuente | URL |
|---|---|
| SUIN-Juriscol | https://www.suin-juriscol.gov.co |
| Gestor Normativo - Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo |
| Relatoría Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/ |
| Relatoría Corte Suprema de Justicia | https://cortesuprema.gov.co/corte/index.php/relatoria/ |
| Buscador Consejo de Estado | https://www.consejodeestado.gov.co/busquedas/buscador-jurisprudencia/ |
| Open Library (ISBN) | https://openlibrary.org |
| doi.org (DOI) | https://doi.org |

---

## 🐛 Solución de problemas frecuentes

**La app muestra "Please wait..." mucho tiempo al cargar:**
- Espere hasta 5 minutos en el primer despliegue. Streamlit instala todas las dependencias.

**Error "ModuleNotFoundError":**
- Verifique que el archivo `requirements.txt` esté en la raíz del repositorio.

**Las verificaciones quedan como "No verificable":**
- Los servidores oficiales pueden estar temporalmente inaccesibles. Consulte manualmente las URLs indicadas.

**El PDF no se lee correctamente:**
- Algunos PDFs escaneados (imágenes) no tienen texto seleccionable. Use primero un OCR externo.

---

## 📞 Soporte

Esta herramienta es de código abierto y uso libre para la comunidad jurídica colombiana.
Para reportar errores o sugerir mejoras, abra un *Issue* en el repositorio de GitHub.

---

*Desarrollado en Python con Streamlit · Cumple Ley 1581/2012 · IA Responsable*
