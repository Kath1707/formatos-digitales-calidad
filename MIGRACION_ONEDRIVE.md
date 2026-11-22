# Historial en OneDrive (Excel) — guía rápida

Las apps pueden guardar el historial en Google Sheets (valor por defecto) o en archivos
Excel de la carpeta **Calidad** del OneDrive de `tu_correo@empresa.pe`.
Cambiar de uno a otro se hace **solo con los Secrets de Streamlit**, sin tocar el código.

## Secrets (nivel superior, sin sección)

```toml
AZURE_TENANT_ID     = "..."
AZURE_CLIENT_ID     = "..."
AZURE_CLIENT_SECRET = "..."                  # el VALOR del secreto, no su ID
ONEDRIVE_USER       = "tu_correo@empresa.pe"
ONEDRIVE_ROOT       = "Calidad"              # opcional

BACKEND = "google"        # "onedrive" para pasar TODAS las apps a OneDrive
# Para probar de a una, añade (tiene prioridad sobre BACKEND):
# BACKEND_HUEVO = "onedrive"      BACKEND_NARANJA  = "onedrive"
# BACKEND_TAMIZADO = "onedrive"   BACKEND_COCINA   = "onedrive"
# BACKEND_PT = "onedrive"         BACKEND_PI       = "onedrive"
# BACKEND_RECLAMOS = "onedrive"   # matriz FMEA + banner de riesgo de PI
```

Mantén `ROOT_FOLDER_ID` y `[gcp_service_account]` mientras alguna app siga en Google.
**Para volver a Google** (si algo falla): borra la línea `BACKEND_...` o ponla en `"google"`.

## Cómo se guarda

| App | Carpeta en OneDrive | Archivo del mes | Hoja (pestaña) |
|---|---|---|---|
| Producto terminado | `Productos terminados` | `<Mes> <Año> - PT.xlsx` | `AAAA-MM-DD` |
| Procesos / PI | `Productos intermedios` | `<Mes> <Año> - PI.xlsx` | `AAAA-MM-DD <Turno>` |
| Cocina dulce | `Insumos cocina` | `<Mes> <Año>.xlsx` | `AAAA-MM-DD <Turno>` |
| Desinfección huevo | `Desinfección huevo` | `<Mes> <Año> - Huevo.xlsx` | `AAAA-MM-DD` |
| Desinfección naranja | `Desinfección naranja` | `<Mes> <Año> - Naranja.xlsx` | `AAAA-MM-DD` |
| Tamizado secos | `Tamizado secos` | `<Mes> <Año> - Tamizado.xlsx` | `AAAA-MM-DD` |
| Reclamos (solo lectura) | `Matriz` | `Consolidado_Reclamos_B2B_STBX.xlsx` | `Reclamos` |

- Si el archivo del mes no existe, **se crea solo** copiando el archivo con "Plantilla" en su
  nombre de esa carpeta. No hay que duplicar nada a mano.
- Cada día (y turno) usa una hoja copiada de `Hoja 1`; **no borres ni renombres `Hoja 1`**.
- Los registros se insertan encima del pie (CONSIDERACIONES / V°B° Coordinadora de Calidad),
  así que la firma y la leyenda legal siempre quedan debajo.
- Si dos personas guardan a la vez, la app vuelve a intentarlo sobre la versión más nueva y
  no se pierde ninguno. Si alguien tiene el Excel abierto, puede tardar unos segundos o pedir
  que lo cierren.
- Los nombres de carpeta no distinguen mayúsculas ni acentos, pero sí deben coincidir en letras.

## Pruebas

`pip install pytest` y luego `pytest tests` — usan las plantillas de `tests/plantillas/` y un
OneDrive simulado; no necesitan internet ni credenciales.
