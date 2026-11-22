"""Ejecuta las páginas de Streamlit de verdad (AppTest) con OneDrive simulado."""
import io
import os
from pathlib import Path

import openpyxl
import pytest
from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def onedrive_activo(nube, monkeypatch):
    monkeypatch.setenv("BACKEND", "onedrive")
    monkeypatch.chdir(RAIZ)
    return nube


def libro(nube, carpeta, nombre):
    return openpyxl.load_workbook(io.BytesIO(nube.archivos[f"Calidad/{carpeta}/{nombre}"]["datos"]))


@pytest.mark.parametrize("pagina,carpeta,sufijo,producto", [
    ("app-desinfeccion-huevo.py", "Desinfección huevo", "Huevo", "Huevo"),
    ("app-desinfeccion-naranja.py", "Desinfección naranja", "Naranja", "Naranja"),
])
def test_desinfeccion_guarda_en_onedrive(onedrive_activo, pagina, carpeta, sufijo, producto):
    at = AppTest.from_file(str(RAIZ / "pages" / pagina), default_timeout=30).run()
    assert not at.exception
    at.text_input[0].set_value("Ana Pérez")      # ejecutor
    at.text_input[1].set_value("Luis Soto")      # supervisor
    at.text_input[2].set_value("Muffin")         # producto a trabajar
    at.button[0].click().run()
    assert not at.exception, at.exception
    assert not at.error, [e.value for e in at.error]
    assert "OneDrive" not in " ".join(m.value for m in at.error)
    hoy = at.date_input[0].value
    wb = libro(onedrive_activo, carpeta, f"{__import__('registro_excel').MESES_ES[hoy.month]} {hoy.year} - {sufijo}.xlsx")
    ws = wb[hoy.strftime("%Y-%m-%d")]
    assert ws["C5"].value == producto and ws["H5"].value == "Ana Pérez" and ws["J5"].value == "Muffin"


def test_tamizado_guarda_en_onedrive(onedrive_activo):
    at = AppTest.from_file(str(RAIZ / "pages" / "app-tamizado-secos.py"), default_timeout=30).run()
    assert not at.exception
    at.text_input[0].set_value("Ana Pérez")
    at.text_input[1].set_value("Luis Soto")
    at.text_input[2].set_value("Muffin")
    at.button[0].click().run()
    assert not at.exception and not at.error, [e.value for e in at.error]
    hoy = at.date_input[0].value
    ws = libro(onedrive_activo, "Tamizado secos", f"{__import__('registro_excel').MESES_ES[hoy.month]} {hoy.year} - Tamizado.xlsx")[hoy.strftime("%Y-%m-%d")]
    assert ws["D5"].value == "Conforme" and ws["E5"].value == "N° 30" and ws["G5"].value == "Ana Pérez"


@pytest.mark.parametrize("pagina", [
    "app-producto-terminado.py", "app-procesos-b2b.py", "app-cocina-dulce.py", "app-matriz-riesgo.py",
])
def test_paginas_cargan_con_onedrive_activo(onedrive_activo, pagina):
    at = AppTest.from_file(str(RAIZ / "pages" / pagina), default_timeout=60).run()
    assert not at.exception, at.exception


def test_matriz_usa_reclamos_de_onedrive(onedrive_activo):
    at = AppTest.from_file(str(RAIZ / "pages" / "app-matriz-riesgo.py"), default_timeout=60).run()
    assert not at.exception and not at.error, [e.value for e in at.error]
    assert at.metric[0].value not in ("0", 0)        # "Reclamos totales"


def test_con_google_por_defecto_nada_cambia(nube, monkeypatch):
    """Sin BACKEND, las apps no tocan OneDrive."""
    monkeypatch.delenv("BACKEND", raising=False)
    monkeypatch.chdir(RAIZ)
    at = AppTest.from_file(str(RAIZ / "pages" / "app-desinfeccion-huevo.py"), default_timeout=30).run()
    assert not at.exception
    n = len(nube.llamadas)
    at.text_input[0].set_value("a"); at.text_input[1].set_value("b"); at.text_input[2].set_value("c")
    at.button[0].click().run()
    assert len(nube.llamadas) == n                    # intentó Google (fallará sin credenciales), no OneDrive
