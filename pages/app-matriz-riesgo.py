"""
Matriz de Riesgo FMEA — Línea B2B Starbucks
=============================================================
Dashboard de solo lectura (no registra nada) que calcula una matriz de riesgo
estilo FMEA (Severidad x Frecuencia = NPR) a partir del histórico de reclamos
B2B/STBX consolidado en Google Sheets. Comparte la lógica de riesgo con la app
de registro (ver utils_riesgo.py) para que el banner del formulario y esta
matriz sean siempre consistentes entre sí.

Secrets necesarios (los mismos que ya usan las demás apps):
[gcp_service_account] ... (bloque de cuenta de servicio) ...

Requisito: el Google Sheet "Consolidado_Reclamos_B2B_STBX" debe estar
compartido (Lector basta) con el correo de esa cuenta de servicio.
"""

import pandas as pd
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_DISPONIBLE = True
except ImportError:
    GSHEETS_DISPONIBLE = False

import utils_riesgo as ur

st.set_page_config(page_title="Matriz FMEA · María Almenara", page_icon="⚠️", layout="wide")

st.title("⚠️ Matriz de Riesgo FMEA — Línea B2B Starbucks")

with st.expander("ℹ️ ¿Qué es esta página y cómo se usa? (leer antes de la primera vez)", expanded=True):
    st.markdown(
        """
**¿Qué es?**
Un análisis de riesgo de la línea B2B/Starbucks basado en el histórico de reclamos de clientes.
En vez de reaccionar reclamo por reclamo, agrupa todos los reclamos por producto y tipo de hallazgo,
y calcula qué combinaciones representan el riesgo más alto para la calidad del producto.

**¿Cómo funciona? (resumen)**
1. Cada reclamo se agrupa por **Producto** y **Tipo de Hallazgo** (ej. "Galleta Chip Chocolate" + "Material extraño").
2. A cada tipo de hallazgo se le asigna una **Severidad** fija (1 a 5) según qué tan grave es para la
   inocuidad/calidad del producto (ej. contaminación = 5, un tema de etiquetado = 3).
3. Se calcula la **Frecuencia** (1 a 5) de cada combinación, según cuántas veces se repitió frente a las demás.
4. Se multiplican: **Severidad × Frecuencia = NPR** (Número Prioritario de Riesgo). A mayor NPR,
   mayor prioridad debería tener esa combinación para una acción correctiva o preventiva.

**¿Para qué le sirve al equipo de Calidad?**
- Ayuda a decidir **en qué enfocar primero** los esfuerzos de mejora, en vez de guiarse solo por el
  reclamo más reciente o más "ruidoso".
- Da una base objetiva y con datos para discutir el riesgo en reuniones de calidad, y sirve como
  evidencia de un **análisis de riesgos sistemático** ante auditoría FSSC 22000.
- No reemplaza el criterio del equipo: es un punto de partida para investigar causa raíz en las
  combinaciones de mayor NPR.
- **No es de uso diario** — está pensada para revisarse periódicamente (reuniones de calidad, antes
  de auditorías), no para abrirla cada mañana. El control del día a día está en el formulario de
  registro (el banner de riesgo que aparece al seleccionar un producto).
"""
    )

with st.expander("📖 Glosario de términos"):
    st.markdown(
        """
- **FMEA (Failure Mode and Effects Analysis / Análisis de Modos de Falla y sus Efectos):**
  metodología de ingeniería de calidad que evalúa cada forma en que un proceso o producto puede
  fallar, y prioriza cuáles merecen atención según su gravedad y frecuencia.
- **NPR (Número Prioritario de Riesgo):** resultado de Severidad × Frecuencia. A mayor NPR, mayor
  prioridad.
- **Severidad:** qué tan grave es un tipo de hallazgo si ocurre (escala 1-5, fija por tipo: p. ej.
  contaminación es más grave que un tema de etiquetado).
- **Frecuencia:** qué tan seguido se repite una combinación Producto × Tipo de Hallazgo, en una
  escala de 1 a 5 relativa a las demás combinaciones (no es el conteo directo de reclamos, sino ese
  conteo reescalado para poder compararlo).
- **Tipo de Hallazgo:** la categoría del problema reportado por el cliente (ej. Contaminación,
  Material extraño, Etiquetado, Calidad/apariencia, Otro).
- **Combinación Producto × Hallazgo:** cada fila de la matriz; agrupa todos los reclamos de un mismo
  producto con el mismo tipo de hallazgo.
- **Reclamos sin producto mapeado:** reclamos cuyo nombre de producto no se pudo relacionar con
  ninguno de los productos del catálogo actual (nombres genéricos o ambiguos); no afectan el cálculo
  de riesgo de ningún producto puntual.
"""
    )

st.caption(
    "Severidad × Frecuencia = NPR (Número Prioritario de Riesgo), calculado sobre el histórico "
    "completo de reclamos B2B/STBX. Dashboard de solo lectura — no registra nada."
)


def get_gsheet_client():
    if not GSHEETS_DISPONIBLE:
        return None
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def _cargar(_gc):
    return ur.cargar_reclamos_df(_gc)


gc = get_gsheet_client()
if gc is None:
    st.error(
        "No se pudo conectar al Google Sheet de reclamos. Revisa que los Secrets "
        "`[gcp_service_account]` estén configurados y que el Sheet esté compartido con esa cuenta "
        "de servicio (botón Compartir → pegar el `client_email` de los Secrets → Lector)."
    )
    st.stop()

with st.spinner("Cargando histórico de reclamos..."):
    df_reclamos = _cargar(gc)

if df_reclamos.empty:
    st.warning("El Sheet de reclamos está vacío o no se pudo leer la hoja 'Reclamos'.")
    st.stop()

fmea = ur.calcular_fmea(df_reclamos)

# ── Métricas rápidas ─────────────────────────────────────────────────────────
n_sin_mapear = df_reclamos["productos_app"].apply(len).eq(0).sum()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Reclamos totales", len(df_reclamos))
col2.metric("Combinaciones Producto × Hallazgo", len(fmea))
col3.metric("NPR más alto", int(fmea["NPR"].max()) if not fmea.empty else "—")
col4.metric("Reclamos sin producto mapeado", int(n_sin_mapear))

if n_sin_mapear:
    with st.expander(f"ℹ️ {n_sin_mapear} reclamos no se pudieron asociar a un producto de catálogo"):
        st.caption(
            "No afectan el riesgo de ningún producto puntual (quedan fuera del cálculo). Vienen de "
            "nombres genéricos o ambiguos en la hoja de Reclamos (ej. 'Muffin', 'Keke', '(sin "
            "especificar)') o de productos fuera de la línea B2B actual. Revisa `MAPEO_PRODUCTO` en "
            "`utils_riesgo.py` si alguno debería mapearse."
        )
        st.dataframe(
            df_reclamos.loc[df_reclamos["productos_app"].apply(len) == 0, ["Año", "Mes", "Producto", "Tipo de Hallazgo"]],
            use_container_width=True, hide_index=True,
        )

st.divider()


# ── Tabla FMEA con semáforo por NPR ──────────────────────────────────────────
def prioridad_npr(val: int) -> str:
    if val >= 15:
        return "🟥 Alta"
    if val >= 8:
        return "🟨 Media"
    return "🟩 Baja"


st.subheader("Matriz FMEA — todas las combinaciones (ordenadas por NPR)")
st.caption(
    "🟥 NPR ≥ 15: prioridad alta · 🟨 NPR 8-14: prioridad media · 🟩 NPR < 8: prioridad baja. "
    "La Severidad es fija por tipo de hallazgo (criterio HACCP/FSSC); la Frecuencia se reescala "
    "1-5 según el conteo relativo de reclamos de esa combinación."
)
fmea_mostrar = fmea.copy()
fmea_mostrar.insert(0, "Prioridad", fmea_mostrar["NPR"].apply(prioridad_npr))
st.dataframe(fmea_mostrar, use_container_width=True, hide_index=True)

st.divider()

# ── Top 10 combinaciones críticas ────────────────────────────────────────────
st.subheader("Top 10 — mayor prioridad de atención")
top10 = fmea.head(10).copy()
top10["Etiqueta"] = top10["Producto"] + " · " + top10["Tipo de Hallazgo"]
st.bar_chart(top10.set_index("Etiqueta")["NPR"])

st.divider()

# ── Riesgo actual por producto (mismo cálculo que el banner del formulario) ──
st.subheader("Riesgo actual por producto (últimos 2 meses, igual que el banner del formulario)")
CANON = [
    "CHESSCAKE BITE", "CINNAMON", "CRUMBLE DE BERRIES", "GALLETA AVELLANA",
    "GALLETA AVENA Y PASAS", "GALLETA CHIP CHOCOLATE", "GALLETA CHOCOCHOCO",
    "GALLETA CRAMBERRIES", "GALLETA DECORADA PUMPKIN", "KEKE DE LIMÓN",
    "KEKE DE ZANAHORIA", "MUFFIN DE BERRIES", "MUFFIN DE CHOCOLATE",
    "MUFFIN DE MANZANA", "MUFFIN DE NARANJA CHIP", "PIE DE LIMON", "TORTA CHOCOLATE",
]
filas_riesgo = []
for p in CANON:
    r = ur.calcular_riesgo_producto(df_reclamos, p)
    filas_riesgo.append({"Producto": p, "Nivel de Riesgo": r["nivel"], "Reclamos recientes": r["n_reclamos"]})
df_riesgo_actual = pd.DataFrame(filas_riesgo).sort_values(
    by="Reclamos recientes", ascending=False
).reset_index(drop=True)

EMOJI_NIVEL = {"Crítico": "🔴 Crítico", "Alto": "🟡 Alto", "Normal": "🟢 Normal"}
df_riesgo_actual["Nivel de Riesgo"] = df_riesgo_actual["Nivel de Riesgo"].map(EMOJI_NIVEL)

st.dataframe(df_riesgo_actual, use_container_width=True, hide_index=True)

st.divider()
if st.button("⬅ Volver al inicio"):
    st.switch_page("streamlit_app.py")
