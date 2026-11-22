"""
utils_riesgo.py
================
Capa de análisis de riesgo basada en el histórico de reclamos B2B/STBX, compartida
entre la app de registro (banner + muestreo adaptativo) y el dashboard de matriz FMEA.

Fuente de datos: Google Sheet "Consolidado_Reclamos_B2B_STBX", hoja "Reclamos"
(exportado originalmente desde SharePoint — ver hoja "Notas y Limitaciones" del
Excel original para el detalle de calidad de datos).

IMPORTANTE (Kath): para que esto funcione en producción, comparte ese Google Sheet
(botón "Compartir") con el correo de la cuenta de servicio que usas en tus Secrets
de Streamlit — el mismo valor del campo "client_email" dentro del bloque
[gcp_service_account]. Con que tenga permiso de "Lector" alcanza.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

try:
    import gspread
    GSHEETS_DISPONIBLE = True
except ImportError:
    GSHEETS_DISPONIBLE = False

# ----------------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------------
RECLAMOS_SHEET_ID = "1ydr-6kbnqzspv0FEZL2BXXwdiRs4BQRz3w9lFC6KoaA"   # Google Sheet (BACKEND = "google")
RECLAMOS_WORKSHEET = "Reclamos"
# Excel en OneDrive (BACKEND = "onedrive"): Calidad/Matriz/Consolidado_Reclamos_B2B_STBX.xlsx, hoja "Reclamos"
RECLAMOS_ONEDRIVE_CARPETA = "Matriz"
RECLAMOS_ONEDRIVE_ARCHIVO = "Consolidado_Reclamos_B2B_STBX.xlsx"

# Severidad fija por tipo de hallazgo (1-5), propuesta ligada a criterio HACCP/FSSC
# (Kath: ajusta si tu jefa o la documentación HACCP ya tienen su propia escala).
SEVERIDAD_POR_TIPO = {
    "Contaminación": 5,       # riesgo de inocuidad — ligado a un CCP
    "Material extraño": 4,    # riesgo físico para el consumidor
    "Etiquetado": 3,          # riesgo de alérgenos/trazabilidad si falla el rótulo
    "Calidad/apariencia": 2,  # no es riesgo de inocuidad
    "Otro": 2,
}

MESES_ORDEN = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Mapeo de nombre libre (columna "Producto" de la hoja de Reclamos, escrita a mano
# durante años) -> producto(s) canónico(s) de la app B2B (specs_df). Un valor puede
# ser una tupla cuando el reclamo mezcla 2 productos en un solo documento.
#
# Kath: revisa esta tabla — quedan deliberadamente SIN MAPEAR (no afectan el riesgo
# de ningún producto puntual) los casos genéricos ("Muffin", "Keke", "Productos"),
# los productos que no están en tu línea B2B actual (Cake Pop, Galleta Osso, Keke de
# Plátano, los "Red Velvet"), y los combos ambiguos. Si alguno sí debería contar,
# agrégalo aquí.
MAPEO_PRODUCTO: dict[str, str | tuple[str, ...]] = {
    "CHEESECAKE BITE": "CHESSCAKE BITE",
    "CINNAMON": "CINNAMON",
    "CINNAMON ROLL": "CINNAMON",
    "CRUMBLE DE BERRIES": "CRUMBLE DE BERRIES",
    "GALLETA AVELLANA": "GALLETA AVELLANA",
    "GALLETA AVENA": "GALLETA AVENA Y PASAS",
    "GALLETA DE PASAS Y AVENA": "GALLETA AVENA Y PASAS",
    "GALLETA CHIP": "GALLETA CHIP CHOCOLATE",
    "GALLETA CHIPS": "GALLETA CHIP CHOCOLATE",
    "GALLETA CHIP CHOCOLATE": "GALLETA CHIP CHOCOLATE",
    "GALLETA CHOCOCHIP": "GALLETA CHIP CHOCOLATE",
    "GALLETA CHOCOCHIPS": "GALLETA CHIP CHOCOLATE",
    "GALLETA CHOCO": "GALLETA CHOCOCHOCO",
    "GALLETA CHOCO CHOCO": "GALLETA CHOCOCHOCO",
    "GALLETA CRANBERRY": "GALLETA CRAMBERRIES",
    "KEKE LIMÓN": "KEKE DE LIMÓN",
    "KEKE DE LIMÓN": "KEKE DE LIMÓN",
    "KEKE ZANAHORIA": "KEKE DE ZANAHORIA",
    "KEKE DE ZANAHORIA": "KEKE DE ZANAHORIA",
    "MUFFIN NARANJA": "MUFFIN DE NARANJA CHIP",
    "MUFFIN DE NARANJA": "MUFFIN DE NARANJA CHIP",
    "MUFFIN DE BERRIES": "MUFFIN DE BERRIES",
    "MUFFIN DE BLUEBERRY": "MUFFIN DE BERRIES",
    "MUFFIN DE CHOCOLATE": "MUFFIN DE CHOCOLATE",
    "MUFFIN DE MANZANA": "MUFFIN DE MANZANA",
    "PIE DE LIMÓN": "PIE DE LIMON",
    "TORTA CHOCOLATE": "TORTA CHOCOLATE",
    "TORTA DE CHOCOLATE": "TORTA CHOCOLATE",
    # combos (afectan a más de un producto)
    "MUFFIN NARANJA Y CHOCOCHIP": ("MUFFIN DE NARANJA CHIP", "GALLETA CHIP CHOCOLATE"),
    "PIE LIMÓN / MUFFIN BERRIES": ("PIE DE LIMON", "MUFFIN DE BERRIES"),
    "KEKE DE LIMÓN Y ZANAHORIA": ("KEKE DE LIMÓN", "KEKE DE ZANAHORIA"),
}


def _normaliza(txt: str) -> str:
    return " ".join(str(txt).strip().upper().split())


def productos_de(producto_reclamo: str) -> list[str]:
    """Traduce el texto libre de un reclamo a 0, 1 o 2 productos canónicos de la app."""
    val = MAPEO_PRODUCTO.get(_normaliza(producto_reclamo))
    if val is None:
        return []
    return [val] if isinstance(val, str) else list(val)


def _primer_mes_anio(mes_texto: str, anio: int) -> tuple[int, int] | None:
    """La hoja de Reclamos a veces tiene 'mes' ambiguo tipo 'abril/mayo': se toma el
    primero (conservador: nunca subestima qué tan reciente es un reclamo)."""
    primero = str(mes_texto).strip().lower().split("/")[0].strip()
    n_mes = MESES_ORDEN.get(primero)
    if n_mes is None:
        return None
    return (int(anio), n_mes)


def _periodo_index(anio: int, mes: int) -> int:
    return anio * 12 + mes


def cargar_reclamos_df(gc) -> pd.DataFrame:
    """Lee la hoja 'Reclamos' del Google Sheet y devuelve un DataFrame con una columna
    extra 'productos_app' (lista de productos canónicos a los que aplica cada fila)."""
    sh = gc.open_by_key(RECLAMOS_SHEET_ID)
    ws = sh.worksheet(RECLAMOS_WORKSHEET)
    return _df_desde_valores(ws.get_all_values())


def cargar_reclamos_df_onedrive() -> pd.DataFrame:
    """Igual que cargar_reclamos_df pero leyendo el Excel de OneDrive (carpeta 'Matriz')."""
    import onedrive_client as od

    hojas = od.leer_hojas(RECLAMOS_ONEDRIVE_CARPETA, RECLAMOS_ONEDRIVE_ARCHIVO, (RECLAMOS_WORKSHEET,))
    if RECLAMOS_WORKSHEET not in hojas:
        raise RuntimeError(
            f"No encontré el archivo '{RECLAMOS_ONEDRIVE_ARCHIVO}' (hoja '{RECLAMOS_WORKSHEET}') en la "
            f"carpeta '{RECLAMOS_ONEDRIVE_CARPETA}' de OneDrive."
        )
    return _df_desde_valores(hojas[RECLAMOS_WORKSHEET])


def _df_desde_valores(valores: list) -> pd.DataFrame:
    """DataFrame de reclamos a partir de los valores (lista de filas de texto) de la hoja.

    No asume que la fila 1 es el encabezado: el Excel original tiene un título y un
    subtítulo en las filas 1-2 antes del encabezado real (fila 4), así que se busca la
    fila que contiene "Producto" y "Tipo de Hallazgo" (robusto a que alguien
    inserte/borre filas arriba después)."""
    if not valores:
        return pd.DataFrame()

    fila_header_idx = next(
        (i for i, fila in enumerate(valores)
         if "Producto" in fila and "Tipo de Hallazgo" in fila),
        None,
    )
    if fila_header_idx is None:
        raise RuntimeError(
            "No encontré la fila de encabezado ('Producto', 'Tipo de Hallazgo') en la "
            "hoja 'Reclamos'. ¿Se movió o renombró alguna columna?"
        )

    encabezado = valores[fila_header_idx]
    n = len(encabezado)
    filas_datos = [
        (list(f) + [""] * n)[:n]  # filas de largo parejo (Excel puede devolver filas más cortas)
        for f in valores[fila_header_idx + 1:] if any(c.strip() for c in f)
    ]
    df = pd.DataFrame(filas_datos, columns=encabezado)
    # columnas sin nombre (celdas vacías a la derecha del encabezado) se descartan
    df = df.loc[:, [c != "" for c in df.columns]]
    if df.empty or "Producto" not in df.columns:
        return pd.DataFrame()

    df["Año"] = pd.to_numeric(df.get("Año"), errors="coerce")
    df["productos_app"] = df["Producto"].apply(productos_de)
    df["_periodo"] = df.apply(
        lambda r: _primer_mes_anio(r.get("Mes", ""), r.get("Año", 0)), axis=1
    )
    return df


def calcular_riesgo_producto(
    df_reclamos: pd.DataFrame,
    producto_app: str,
    fecha_ref: date | None = None,
    ventana_meses: int = 2,
    umbral_alto: int = 2,
    umbral_critico: int = 3,
) -> dict:
    """Nivel de riesgo de un producto según sus reclamos en los últimos N meses
    calendario (la hoja de Reclamos solo tiene año+mes, no día exacto — por eso la
    ventana es en meses, no en días)."""
    fecha_ref = fecha_ref or date.today()
    periodo_ref = _periodo_index(fecha_ref.year, fecha_ref.month)
    periodo_min = periodo_ref - (ventana_meses - 1)

    if df_reclamos.empty:
        return {"nivel": "Normal", "n_reclamos": 0, "ventana_meses": ventana_meses, "detalle": []}

    mask_producto = df_reclamos["productos_app"].apply(lambda lst: producto_app in lst)
    df_prod = df_reclamos[mask_producto].copy()

    df_prod["_periodo_idx"] = df_prod["_periodo"].apply(
        lambda p: _periodo_index(*p) if p else None
    )
    df_recientes = df_prod[df_prod["_periodo_idx"].notna() & (df_prod["_periodo_idx"] >= periodo_min)]

    n = len(df_recientes)
    if n >= umbral_critico:
        nivel = "Crítico"
    elif n >= umbral_alto:
        nivel = "Alto"
    else:
        nivel = "Normal"

    detalle = [
        {"año": row["Año"], "mes": row["Mes"], "tipo": row["Tipo de Hallazgo"]}
        for _, row in df_recientes.iterrows()
    ]
    return {"nivel": nivel, "n_reclamos": n, "ventana_meses": ventana_meses, "detalle": detalle}


def calcular_fmea(df_reclamos: pd.DataFrame) -> pd.DataFrame:
    """Matriz FMEA simplificada: una fila por combinación (Producto, Tipo de
    Hallazgo) con al menos 1 reclamo. Severidad fija por tipo (SEVERIDAD_POR_TIPO),
    Frecuencia = conteo de esa combinación re-escalado a 1-5 por cuartiles sobre
    todas las combinaciones observadas, NPR = Severidad x Frecuencia."""
    if df_reclamos.empty:
        return pd.DataFrame(
            columns=["Producto", "Tipo de Hallazgo", "N° Reclamos", "Severidad", "Frecuencia", "NPR"]
        )

    filas = df_reclamos.explode("productos_app")
    filas = filas[filas["productos_app"].notna() & (filas["productos_app"] != "")]

    conteo = (
        filas.groupby(["productos_app", "Tipo de Hallazgo"])
        .size()
        .reset_index(name="N° Reclamos")
        .rename(columns={"productos_app": "Producto"})
    )
    if conteo.empty:
        return conteo

    def frecuencia_1_5(n, n_max):
        if n_max <= 1:
            return 5 if n >= 1 else 1
        # escala lineal 1-5 según el conteo relativo al máximo observado
        return max(1, min(5, round(1 + 4 * (n - 1) / (n_max - 1))))

    n_max = conteo["N° Reclamos"].max()
    conteo["Severidad"] = conteo["Tipo de Hallazgo"].map(SEVERIDAD_POR_TIPO).fillna(2).astype(int)
    conteo["Frecuencia"] = conteo["N° Reclamos"].apply(lambda n: frecuencia_1_5(n, n_max))
    conteo["NPR"] = conteo["Severidad"] * conteo["Frecuencia"]

    return conteo.sort_values("NPR", ascending=False).reset_index(drop=True)
