"""Pruebas con las plantillas REALES de OneDrive y un Graph simulado."""
import io
from datetime import date

import openpyxl
import pytest

import onedrive_client as od
import registro_excel as rx

HOY = date(2026, 11, 22)
TITULO = "2026-11-22"


def abrir(nube, carpeta, nombre):
    return openpyxl.load_workbook(io.BytesIO(nube.archivos[f"Calidad/{carpeta}/{nombre}"]["datos"]))


def fila_de(ws, predicado, desde=1):
    for f in ws.iter_rows(min_row=desde):
        for c in f:
            if c.value is not None and predicado(str(c.value)):
                return c.row


def comprobar_estructura(ws):
    """Invariantes: logo en A1, merges sin solaparse, una sola hoja seleccionada."""
    assert len(ws._images) == 1 and ws._images[0].anchor._from.row == 0
    rangos = list(ws.merged_cells.ranges)
    for i, a in enumerate(rangos):
        for b in rangos[i + 1:]:
            assert a.isdisjoint(b), f"merges solapados {a} {b}"


# ---------------------------------------------------------------- modo firma
@pytest.mark.parametrize("fmt", [rx.HUEVO, rx.NARANJA, rx.TAMIZADO])
def test_firma_crea_libro_llena_libres_e_inserta(nube, fmt):
    ncols = {"huevo": 11, "naranja": 11, "tamizado": 10}[fmt.app]
    libres = {"huevo": 1, "naranja": 1, "tamizado": 3}[fmt.app]
    total = libres + 2
    usadas = []
    for i in range(total):
        fila = ["22/11/2026"] + [f"dato{i}-{c}" for c in range(2, ncols + 1)]
        nombre, usada = rx.guardar_fila_con_firma(fmt, HOY, TITULO, fila)
        usadas.append(usada)
    assert nombre == f"Noviembre 2026{fmt.sufijo}.xlsx"
    wb = abrir(nube, fmt.carpeta, nombre)
    assert wb.sheetnames == [TITULO, "Hoja 1"]            # nueva primero, plantilla al final
    ws = wb[TITULO]
    comprobar_estructura(ws)
    assert usadas == list(range(5, 5 + total))             # primero las libres, luego inserta
    for i in range(total):
        assert ws.cell(5 + i, 2).value == f"dato{i}-2"
        assert ws.cell(5 + i, 1).value.strftime("%d/%m/%Y") == "22/11/2026"   # fecha real
        assert ws.cell(5 + i, 1).border.left.style == "thin"
    # la leyenda de la firma sigue 1 fila por debajo de la fila de firma y la plantilla quedó intacta
    ley = fila_de(ws, lambda t: "COORDINADORA DE CALIDAD" in t.upper() and t.strip().upper().startswith("V"), desde=5)
    assert ley == 5 + total + 1
    plantilla = wb["Hoja 1"]
    assert fila_de(plantilla, lambda t: "COORDINADORA DE CALIDAD" in t.upper() and t.strip().upper().startswith("V"), desde=5) \
        == {"huevo": 7, "naranja": 7, "tamizado": 9}[fmt.app]
    assert not any(c.value for c in plantilla[5])
    # la leyenda legal también bajó y su combinada la acompaña
    legal = fila_de(ws, lambda t: t.startswith("Se prohíbe"))
    assert legal == ley + 1
    assert any(r.min_row == legal and r.max_row == legal for r in ws.merged_cells.ranges)


def test_segundo_dia_y_mismo_libro(nube):
    rx.guardar_fila_con_firma(rx.HUEVO, HOY, "2026-11-22", ["22/11/2026"] + ["a"] * 10)
    rx.guardar_fila_con_firma(rx.HUEVO, date(2026, 11, 23), "2026-11-23", ["23/11/2026"] + ["b"] * 10)
    wb = abrir(nube, "Desinfección huevo", "Noviembre 2026 - Huevo.xlsx")
    assert wb.sheetnames == ["2026-11-23", "2026-11-22", "Hoja 1"]
    assert sum(1 for w in wb.worksheets if w.sheet_view.tabSelected) == 1
    assert wb["2026-11-23"]["B5"].value == "b" and wb["2026-11-22"]["B5"].value == "a"


# --------------------------------------------------------------- modo footer
def filas_pt(n, extra=""):
    return [[("22/11/2026" if c == 0 else f"{extra}x{c}") for c in range(27)] for _ in range(n)]


def test_pt_borra_ejemplos_e_inserta_sobre_consideraciones(nube):
    filas = [["22/11/2026", "PRODUCCIÓN", "STARBUCKS", i + 1, "GALLETA CHIP", "Línea 1", "326", "22/11/2026", "13/12/2026",
              "≤ 25", 270.5, "8,2", "", "", 3.1, "Conforme", "Conforme", "Conforme", "C", "C", "C", "C", "C", "B-01", "T-02", "C", "VI"]
             for i in range(3)]
    nombre = rx.guardar_filas(rx.PT, HOY, TITULO, filas, ajustar_extras=True)
    assert nombre == "Noviembre 2026 - PT.xlsx"
    rx.guardar_filas(rx.PT, HOY, TITULO, filas_pt(3), ajustar_extras=True)   # segundo producto, misma hoja
    wb = abrir(nube, "Productos terminados", nombre)
    ws = wb[TITULO]
    comprobar_estructura(ws)
    assert [ws.cell(r, 4).value for r in range(5, 8)] == [1, 2, 3]            # sin los 1.0/2.0/3.0 de ejemplo
    assert ws["G5"].value == 326 and ws["K5"].value == 270.5 and ws["L5"].value == 8.2
    assert ws["Z5"].value == "C" or ws["AA5"].value == "VI"
    pie = fila_de(ws, lambda t: t.upper().startswith("CONSIDERACIONES"))
    assert pie == 5 + 6                                                       # 6 filas de datos
    # firma y leyenda legal conservan su posición relativa respecto al pie
    plantilla = wb["Hoja 1"]
    pie_pl = fila_de(plantilla, lambda t: t.upper().startswith("CONSIDERACIONES"))
    assert pie_pl == 41
    assert fila_de(ws, lambda t: "COORDINADORA" in t.upper(), desde=pie) - pie == fila_de(plantilla, lambda t: "COORDINADORA" in t.upper(), desde=41) - 41
    assert fila_de(ws, lambda t: t.startswith("Se prohíbe")) - pie == 46 - 41
    # combinadas del pie se movieron con él
    assert any(r.min_row == pie and r.max_row == pie + 1 and r.max_col == 27 for r in ws.merged_cells.ranges)


def test_pi_encuentra_pie_en_fila_8_no_en_la_27(nube):
    filas = [["22/11/2026", "PRODUCCIÓN", "STARBUCKS", i + 1] + ["v"] * 24 for i in range(4)]
    rx.guardar_filas(rx.PI, HOY, f"{TITULO} Día", filas)
    ws = abrir(nube, "Productos intermedios", "Noviembre 2026 - PI.xlsx")[f"{TITULO} Día"]
    comprobar_estructura(ws)
    pie = fila_de(ws, lambda t: "COORDINADORA" in t.upper())
    assert pie == 5 + 4                      # datos 5..8, firma en 9
    assert ws.max_row <= 27 + 1               # nada se fue al final de la hoja
    assert ws["A5"].value.strftime("%d/%m/%Y") == "22/11/2026" and ws["AB8"].value == "v"
    # el texto suelto 'VB° Jefe de Calidad' de la plantilla (P27) no engañó a la búsqueda
    assert fila_de(ws, lambda t: "Jefe de Calidad" in t) == 27 - 3 + 4


def test_cocina_inserta_con_bordes_aunque_la_plantilla_no_los_tenga(nube):
    filas = [["22/11/2026", "COCINA", "STARBUCKS", i + 1, "FUDGE"] + ["x"] * 16 for i in range(2)]
    rx.guardar_filas(rx.COCINA, HOY, f"{TITULO} Día", filas)
    wb = abrir(nube, "Insumos cocina", "Noviembre 2026.xlsx")
    ws = wb[f"{TITULO} Día"]
    comprobar_estructura(ws)
    assert ws["E5"].value == "FUDGE" and ws["U6"].value == "x"
    assert all(ws.cell(5, c).border.left.style == "thin" for c in range(1, 22))
    assert fila_de(ws, lambda t: "COORDINADORA" in t.upper()) == 7


def test_texto_libre_nunca_se_vuelve_formula(nube):
    fila = ["22/11/2026", "L", "P", "T", "N° 30", "=SUMA(1+1)", "-cuidado", "@x", "007", "V"]
    rx.guardar_fila_con_firma(rx.TAMIZADO, HOY, TITULO, fila)
    ws = abrir(nube, "Tamizado secos", "Noviembre 2026 - Tamizado.xlsx")[TITULO]
    assert ws["F5"].value == "=SUMA(1+1)" and ws["F5"].data_type == "s"
    assert ws["G5"].value == "-cuidado" and ws["I5"].value == "007"


# ------------------------------------------------------------ concurrencia
def test_conflicto_412_se_reintenta_y_conserva_ambos_registros(nube):
    rx.guardar_fila_con_firma(rx.HUEVO, HOY, TITULO, ["22/11/2026"] + ["primero"] * 10)

    def otro_usuario_guarda(ruta):
        # alguien guarda JUSTO antes de que llegue nuestra subida
        wb = openpyxl.load_workbook(io.BytesIO(nube.archivos[ruta]["datos"]))
        wb[TITULO]["K20"] = "huella-del-otro"
        buf = io.BytesIO(); wb.save(buf)
        nube.archivos[ruta] = {"datos": buf.getvalue(), "v": nube.archivos[ruta]["v"] + 1}

    nube.interferir = otro_usuario_guarda
    rx.guardar_fila_con_firma(rx.HUEVO, HOY, TITULO, ["22/11/2026"] + ["segundo"] * 10)
    ws = abrir(nube, "Desinfección huevo", "Noviembre 2026 - Huevo.xlsx")[TITULO]
    assert ws["B5"].value == "primero" and ws["B6"].value == "segundo"
    assert fila_de(ws, lambda t: t == "huella-del-otro") is not None   # lo del otro usuario NO se perdió


def test_creacion_simultanea_no_duplica(nube):
    def otro_crea(ruta):
        nube.archivos[ruta] = {"datos": (nube.archivos["Calidad/Desinfección huevo/Control desinfeccion huevo - Plantilla base.xlsx"]["datos"]), "v": 1}

    nube.interferir = otro_crea
    rx.guardar_fila_con_firma(rx.HUEVO, HOY, TITULO, ["22/11/2026"] + ["a"] * 10)
    ws = abrir(nube, "Desinfección huevo", "Noviembre 2026 - Huevo.xlsx")[TITULO]
    assert ws["B5"].value == "a"


# ------------------------------------------------------------------ lectura
def test_lectura_de_productos_del_dia(nube):
    f = [["22/11/2026", "P", "STARBUCKS", 1, "GALLETA CHIP"] + [""] * 22]
    rx.guardar_filas(rx.PT, HOY, TITULO, f)
    hojas = rx.leer_hojas_del_dia(rx.PT, HOY, [TITULO, "2026-11-21"])
    assert list(hojas) == [TITULO]
    enc, filas = rx.filas_de_datos(hojas[TITULO], rx.PT)
    assert enc[4] == "Producto" and [x[4] for x in filas] == ["GALLETA CHIP"]
    assert rx.leer_hojas_del_dia(rx.PT, date(2026, 12, 1), [TITULO]) == {}     # libro del mes aún no existe


def test_nombres_con_acentos_y_mayusculas_se_resuelven(nube):
    assert od.resolver_carpeta("desinfeccion HUEVO") == "Desinfección huevo"
    with pytest.raises(od.ArchivoNoEncontrado):
        od.resolver_carpeta("No existe")


# ----------------------------------------------------------------- reclamos
def test_reclamos_desde_onedrive_igual_que_desde_google(nube):
    import utils_riesgo as ur

    df = ur.cargar_reclamos_df_onedrive()
    assert len(df) == 7
    assert {"Producto", "Tipo de Hallazgo", "productos_app", "_periodo"} <= set(df.columns)
    assert df["Año"].min() == 2021 and df["Año"].notna().all()      # 2021.0 del Excel → número
    fmea = ur.calcular_fmea(df)
    assert not fmea.empty and fmea["NPR"].max() >= 1
    # 3 reclamos de Galleta Chip (oct + 2 en nov) dentro de la ventana de 2 meses → Crítico
    r = ur.calcular_riesgo_producto(df, "GALLETA CHIP CHOCOLATE", fecha_ref=date(2026, 11, 22))
    assert r["nivel"] == "Crítico" and r["n_reclamos"] == 3
