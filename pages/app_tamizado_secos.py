"""
Control de Tamizado de Insumos Secos — María Almenara
=====================================================

App Streamlit para registrar el control de tamizado de insumos secos
(colador N° 30), con el mismo patrón que la app de Desinfección de Huevo:
- Carpeta en Drive: "Tamizado secos" (misma raíz que las demás carpetas)
- Spreadsheet mensual: "<Mes> <Año> - Tamizado" (debe existir previamente,
  con la plantilla en "Hoja 1")
- Cada FECHA usa/crea una hoja (tab) dentro del spreadsheet mensual,
  duplicando "Hoja 1" la primera vez que se usa esa fecha.

Columnas del registro (A:J, en este orden):
FECHA | LÍNEA | PRODUCTO | TAMIZADO | #TAMAÑO TAMIZ | ACCIÓN CORRECTIVA |
EJECUTOR | MIEMBRO DE CALIDAD | PRODUCTO A TRABAJAR | VºBº COORDINADORA DE CALIDAD

Dónde se guarda cada registro:
- Primero se llenan las filas libres entre el encabezado (fila 4) y la fila
  de la imagen de la firma (filas 5, 6, 7 en la plantilla).
- Cuando ya no hay filas libres, se INSERTA una fila nueva justo encima de la
  fila de la firma, empujándola hacia abajo sin pisarla ni desordenar nada.
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

# ──────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN — AJUSTA ESTOS VALORES SEGÚN CORRESPONDA
# ──────────────────────────────────────────────────────────────────────────
CARPETA_NOMBRE = "Tamizado secos"               # ⚠️ AJUSTA si el nombre exacto de tu carpeta en Drive es distinto
SUFIJO_SPREADSHEET = "Tamizado"                 # ⚠️ spreadsheet mensual: "Noviembre 2026 - Tamizado"
HOJA_PLANTILLA = "Hoja 1"                       # hoja plantilla dentro de cada spreadsheet mensual
FILA_ENCABEZADO = 4                             # fila de los títulos de columna (A4:J4)
ULTIMA_COLUMNA = "J"                            # última columna del registro
MARCADOR_FIRMA = "COORDINADORA DE CALIDAD"      # leyenda ubicada justo DEBAJO de la imagen de la firma (no tocar)

# Valores fijos del registro (se muestran como recordatorio y se guardan en cada fila).
CAMPOS_FIJOS = {
    "LÍNEA": "PROCESOS",
    "#TAMAÑO TAMIZ": "N° 30",
    "VºBº COORDINADORA DE CALIDAD": "V. IRIARTE",
}

# Insumos secos que se pueden elegir (edita esta lista). "Otro" permite escribir uno distinto.
OPCIONES_INSUMO = ["Harina", "Azúcar", "Polvos", "Otro"]
OPCION_OTRO = "Otro"
OPCIONES_TAMIZADO = ["Conforme", "No conforme"]
COMENTARIO_VACIO = "Sin comentarios correctivos"

# ──────────────────────────────────────────────────────────────────────────
# CONEXIÓN A GOOGLE DRIVE / SHEETS
# ──────────────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def conectar_gspread():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds)


def obtener_carpeta_id(gc, nombre_carpeta, root_folder_id):
    """Busca una subcarpeta por nombre dentro de ROOT_FOLDER_ID."""
    resp = gc.http_client.request(
        "get",
        "https://www.googleapis.com/drive/v3/files",
        params={
            "q": (
                f"'{root_folder_id}' in parents and "
                f"name = '{nombre_carpeta}' and "
                "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            ),
            "fields": "files(id, name)",
        },
    )
    archivos = resp.json().get("files", [])
    if not archivos:
        raise FileNotFoundError(
            f"No se encontró la carpeta '{nombre_carpeta}' dentro de la carpeta raíz. "
            "Verifica el nombre exacto y que la cuenta de servicio tenga acceso."
        )
    return archivos[0]["id"]


def obtener_spreadsheet_mensual(gc, carpeta_id, nombre_spreadsheet):
    """Busca (no crea) el spreadsheet mensual dentro de la carpeta de tamizado."""
    resp = gc.http_client.request(
        "get",
        "https://www.googleapis.com/drive/v3/files",
        params={
            "q": (
                f"'{carpeta_id}' in parents and "
                f"name = '{nombre_spreadsheet}' and "
                "mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
            ),
            "fields": "files(id, name)",
        },
    )
    archivos = resp.json().get("files", [])
    if not archivos:
        raise FileNotFoundError(
            f"No se encontró el spreadsheet '{nombre_spreadsheet}' dentro de la carpeta "
            f"'{CARPETA_NOMBRE}'. Confirma que el nombre coincide exactamente."
        )
    return gc.open_by_key(archivos[0]["id"])


def nombre_spreadsheet_mensual(fecha: date) -> str:
    meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
    }
    return f"{meses[fecha.month]} {fecha.year} - {SUFIJO_SPREADSHEET}"


def obtener_o_crear_hoja_del_dia(spreadsheet, fecha: date):
    """Devuelve la hoja (tab) de la fecha, duplicando la plantilla si no existe."""
    nombre_tab = fecha.strftime("%Y-%m-%d")
    try:
        return spreadsheet.worksheet(nombre_tab)
    except gspread.WorksheetNotFound:
        plantilla = spreadsheet.worksheet(HOJA_PLANTILLA)
        return plantilla.duplicate(new_sheet_name=nombre_tab)


def encontrar_fila_firma(worksheet):
    """
    Ubica la fila de la IMAGEN de firma: la fila inmediatamente anterior a la
    leyenda "VºB COORDINADORA DE CALIDAD" (MARCADOR_FIRMA). Se busca solo debajo
    del encabezado.
    """
    valores_col_a = worksheet.col_values(1)
    for idx in range(FILA_ENCABEZADO + 1, len(valores_col_a) + 1):
        if MARCADOR_FIRMA in (valores_col_a[idx - 1] or ""):
            return idx - 1
    raise ValueError(
        f"No se encontró la leyenda '{MARCADOR_FIRMA}' en la hoja. "
        "Verifica que la plantilla no haya cambiado de estructura."
    )


def guardar_registro(
    worksheet, fecha, producto, tamizado, accion_correctiva,
    ejecutor, miembro_calidad, producto_a_trabajar,
):
    fila_firma = encontrar_fila_firma(worksheet)
    nueva_fila = [
        fecha.strftime("%d/%m/%Y"),
        CAMPOS_FIJOS["LÍNEA"],
        producto,
        tamizado,
        CAMPOS_FIJOS["#TAMAÑO TAMIZ"],
        accion_correctiva,
        ejecutor,
        miembro_calidad,
        producto_a_trabajar,
        CAMPOS_FIJOS["VºBº COORDINADORA DE CALIDAD"],
    ]

    # 1) ¿Hay una fila libre entre el encabezado y la firma? (filas 5, 6, 7 de la plantilla)
    primera = FILA_ENCABEZADO + 1
    ultima = fila_firma - 1
    if ultima >= primera:
        existentes = worksheet.get(f"A{primera}:{ULTIMA_COLUMNA}{ultima}")
        for i in range(ultima - primera + 1):
            fila = existentes[i] if i < len(existentes) else []
            if all(not str(celda).strip() for celda in fila):
                destino = primera + i
                worksheet.update(
                    values=[nueva_fila],
                    range_name=f"A{destino}:{ULTIMA_COLUMNA}{destino}",
                    value_input_option="USER_ENTERED",
                )
                return destino

    # 2) Sin filas libres: se INSERTA una fila nueva justo encima de la firma,
    #    empujando la imagen y la leyenda hacia abajo.
    worksheet.insert_row(nueva_fila, index=fila_firma, value_input_option="USER_ENTERED")
    return fila_firma


# ──────────────────────────────────────────────────────────────────────────
# INTERFAZ STREAMLIT
# ──────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Control Tamizado Secos", page_icon="🥣", layout="centered")

st.title("🥣 Control de Tamizado de Insumos Secos")
st.caption("Control de procesos · María Almenara")

with st.expander("ℹ️ Recordatorio del proceso", expanded=True):
    st.markdown(
        f"""
        - **Línea:** {CAMPOS_FIJOS['LÍNEA']}
        - **Colador:** {CAMPOS_FIJOS['#TAMAÑO TAMIZ']} (abertura aprox. 0.6 mm)
        - **Frecuencia:** por cada lote o cantidad de insumo seco que se tamice, antes de su uso en el proceso.
        - Si se encuentran materias extrañas en el colador: retirarlas, registrar el hallazgo y volver a tamizar el insumo.
        - Si el colador presenta rotura o deformación: reemplazarlo y volver a tamizar el insumo tamizado previamente.
        - Si el insumo no fue tamizado antes de su uso: detener el uso, tamizar el insumo y evaluar el producto elaborado.
        """
    )

st.divider()
st.subheader("Nuevo registro")

if "form_key" not in st.session_state:
    st.session_state.form_key = 0

k = st.session_state.form_key  # sufijo de las keys, cambia al pulsar "Nuevo registro"

fecha_seleccionada = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY", key=f"fecha_{k}")

insumo_elegido = st.selectbox("Producto (insumo seco tamizado)", options=OPCIONES_INSUMO, key=f"insumo_{k}")
if insumo_elegido == OPCION_OTRO:
    producto = st.text_input("Escribe el insumo", placeholder="Nombre del insumo seco", key=f"insumo_otro_{k}")
else:
    producto = insumo_elegido

tamizado = st.selectbox("Tamizado", options=OPCIONES_TAMIZADO, key=f"tamizado_{k}")

dejar_sin_comentario = st.checkbox("Dejar acción correctiva vacía", value=True, key=f"sin_comentario_{k}")
if dejar_sin_comentario:
    accion_correctiva = COMENTARIO_VACIO
    st.caption(f"Se guardará como: “{COMENTARIO_VACIO}”")
else:
    accion_correctiva = st.text_area(
        "Comentario de acción correctiva", placeholder="Escribe el comentario...", key=f"accion_{k}"
    )

ejecutor = st.text_input("Ejecutor", placeholder="Nombre completo", key=f"ejecutor_{k}")
miembro_calidad = st.text_input(
    "Miembro de Calidad que registró", placeholder="Nombre completo", key=f"miembro_calidad_{k}"
)
producto_a_trabajar = st.text_input(
    "Producto a trabajar", placeholder="Producto para el que se usará este insumo", key=f"producto_trabajar_{k}"
)

st.divider()

col_guardar, col_nuevo = st.columns(2)

with col_guardar:
    if st.button("💾 Guardar registro", type="primary", use_container_width=True):
        if not producto.strip():
            st.error("Por favor escribe el insumo seco tamizado antes de guardar.")
        elif not ejecutor.strip():
            st.error("Por favor ingresa el nombre del ejecutor antes de guardar.")
        elif not miembro_calidad.strip():
            st.error("Por favor ingresa el nombre del miembro de Calidad antes de guardar.")
        elif not producto_a_trabajar.strip():
            st.error("Por favor ingresa el producto a trabajar antes de guardar.")
        elif not dejar_sin_comentario and not accion_correctiva.strip():
            st.error("Escribe un comentario de acción correctiva o marca la casilla para dejarlo vacío.")
        else:
            accion_final = accion_correctiva if dejar_sin_comentario else accion_correctiva.strip()
            try:
                with st.spinner("Guardando en Google Sheets..."):
                    gc = conectar_gspread()
                    root_folder_id = st.secrets["ROOT_FOLDER_ID"]
                    carpeta_id = obtener_carpeta_id(gc, CARPETA_NOMBRE, root_folder_id)
                    nombre_ss = nombre_spreadsheet_mensual(fecha_seleccionada)
                    spreadsheet = obtener_spreadsheet_mensual(gc, carpeta_id, nombre_ss)
                    worksheet = obtener_o_crear_hoja_del_dia(spreadsheet, fecha_seleccionada)
                    guardar_registro(
                        worksheet, fecha_seleccionada, producto.strip(), tamizado, accion_final,
                        ejecutor.strip(), miembro_calidad.strip(), producto_a_trabajar.strip(),
                    )
                st.success(
                    f"✅ Registro guardado correctamente en '{nombre_ss}' → "
                    f"hoja '{fecha_seleccionada.strftime('%Y-%m-%d')}'."
                )
                st.balloons()
            except FileNotFoundError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Ocurrió un error al guardar: {e}")

with col_nuevo:
    if st.button("➕ Nuevo registro", use_container_width=True):
        st.session_state.form_key += 1
        st.rerun()
