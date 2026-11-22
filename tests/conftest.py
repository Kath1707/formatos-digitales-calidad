"""Simula Microsoft Graph en memoria para probar sin internet ni credenciales."""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
PLANTILLAS = Path(__file__).resolve().parent / "plantillas"

# carpeta de OneDrive -> archivos de plantilla que contiene
ESTRUCTURA = {
    "Productos terminados": ["Liberacion PT - Plantilla Base.xlsx"],
    "Productos intermedios": ["Proceso PI - Plantilla Base.xlsx"],
    "Insumos cocina": ["Insumos cocina - Plantilla base.xlsx"],
    "Desinfección huevo": ["Control desinfeccion huevo - Plantilla base.xlsx"],
    "Desinfección naranja": ["Control desinfeccion naranja - Plantilla base.xlsx"],
    "Tamizado secos": ["Control tamizado secos - Plantilla base.xlsx"],
    "Matriz": ["Consolidado_Reclamos_B2B_STBX.xlsx"],   # se genera con datos INVENTADOS (ver abajo)
}


def reclamos_sintetico() -> bytes:
    """Excel de reclamos con la misma estructura que el real pero datos inventados
    (el repo es público: los reclamos reales de clientes no deben subirse)."""
    import io
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reclamos"
    ws["A1"] = "Consolidado de Reclamos B2B/STBX (datos de prueba)"
    ws.append([]); ws.append([])
    ws.append(["ID", "Año", "Mes", "N° Reclamo", "Producto", "Tipo de Hallazgo",
               "Detalle del Hallazgo", "Cliente", "Archivo de Origen", "Observaciones"])
    datos = [
        (2021, "abril", "Muffin de Manzana", "Otro"),
        (2025, "julio", "Muffin de Blueberry", "Calidad/apariencia"),
        (2026, "octubre", "Galleta Chip", "Material extraño"),
        (2026, "noviembre", "Galleta Chip", "Contaminación"),
        (2026, "noviembre", "Galleta Chip", "Etiquetado"),
        (2026, "noviembre", "Pie de Limón", "Calidad/apariencia"),
        (2026, "abril/mayo", "(sin especificar)", "Otro"),
    ]
    for i, (anio, mes, prod, tipo) in enumerate(datos, start=1):
        ws.append([float(i), float(anio), mes, f"R{i}", prod, tipo, "detalle", "STBX", "x.pdf", ""])
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()


class Resp:
    def __init__(self, status=200, datos=None, contenido=b"", headers=None):
        self.status_code, self._datos, self.content, self.headers = status, datos, contenido, headers or {}

    def json(self):
        return self._datos


class FakeGraph:
    def __init__(self):
        self.archivos = {}   # "Calidad/Carpeta/archivo.xlsx" -> {"datos": bytes, "v": int}
        self.llamadas = []
        self.interferir = None  # callable(ruta) -> se ejecuta justo antes de aceptar un PUT (simula otro usuario)
        for carpeta, nombres in ESTRUCTURA.items():
            for n in nombres:
                datos = reclamos_sintetico() if carpeta == "Matriz" else (PLANTILLAS / n).read_bytes()
                self.archivos[f"Calidad/{carpeta}/{n}"] = {"datos": datos, "v": 1}

    def etag(self, ruta):
        return f'"{{ABC}},{self.archivos[ruta]["v"]}"'

    def http(self, metodo, url, headers=None, reintentos=0, **kw):
        base = re.match(r".*/drive/root:/(.*)$", url).group(1)
        ruta, _, query = base.partition("?")
        ruta = unquote(ruta)
        sufijo = ""
        for s in (":/children", ":/content", ":/createUploadSession"):
            if ruta.endswith(s):
                ruta, sufijo = ruta[: -len(s)], s
        self.llamadas.append((metodo, ruta, sufijo))
        headers = headers or {}

        if sufijo == ":/children":
            prefijo = ruta + "/"
            hijos, carpetas = [], set()
            for k, a in self.archivos.items():
                if k.startswith(prefijo):
                    resto = k[len(prefijo):]
                    if "/" in resto:
                        carpetas.add(resto.split("/")[0])
                    else:
                        hijos.append({"name": resto, "file": {}, "size": len(a["datos"]), "eTag": self.etag(k)})
            hijos += [{"name": c, "folder": {}} for c in sorted(carpetas)]
            if not hijos:
                return Resp(404, {"error": {"message": "no existe"}})
            return Resp(200, {"value": hijos})

        if metodo == "GET" and sufijo == "":
            if ruta not in self.archivos:
                return Resp(404, {"error": {"message": "no existe"}})
            return Resp(200, {"eTag": self.etag(ruta), "size": len(self.archivos[ruta]["datos"])})

        if metodo == "GET" and sufijo == ":/content":
            if ruta not in self.archivos:
                return Resp(404, {"error": {"message": "no existe"}})
            return Resp(200, contenido=self.archivos[ruta]["datos"])

        if metodo == "PUT" and sufijo == ":/content":
            if self.interferir:
                f, self.interferir = self.interferir, None
                f(ruta)
            existe = ruta in self.archivos
            if "conflictBehavior=fail" in query and existe:
                return Resp(409, {"error": {"message": "ya existe"}})
            if "If-Match" in headers and (not existe or headers["If-Match"] != self.etag(ruta)):
                return Resp(412, {"error": {"message": "precondición"}})
            v = self.archivos[ruta]["v"] + 1 if existe else 1
            self.archivos[ruta] = {"datos": kw["data"], "v": v}
            return Resp(200 if existe else 201, {})
        raise AssertionError(f"llamada no simulada: {metodo} {url}")


@pytest.fixture
def nube(monkeypatch):
    import onedrive_client as od

    g = FakeGraph()
    monkeypatch.setenv("ONEDRIVE_USER", "khidalgo@mariaalmenara.pe")
    monkeypatch.setenv("ONEDRIVE_ROOT", "Calidad")
    monkeypatch.setattr(od, "_http", g.http)
    monkeypatch.setattr(od, "time", type("T", (), {"sleep": staticmethod(lambda s: None), "time": staticmethod(__import__("time").time)}))
    od._cache_carpetas.clear()
    od.leer_hojas_cacheado.clear()
    return g
