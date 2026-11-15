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
