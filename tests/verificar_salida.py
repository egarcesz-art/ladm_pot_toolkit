"""Verificaciones automáticas de la prueba integral (afirmaciones sobre la salida real)."""
import sys
from pathlib import Path

import pandas as pd
import pyogrio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ladm_pot.modelo import Catalogo  # noqa: E402

fallos = []
def check(cond, msg):
    print(("OK   " if cond else "FALLA") + " " + msg)
    if not cond:
        fallos.append(msg)

s1, s2 = (next(Path(p).glob("LADM_COL_POT_*")) for p in sys.argv[1:3])
cat = Catalogo(s2 / "06_DOCUMENTACION_TECNICA" / "modelo_oficial_usado")
# Pasada 1: lo inseguro queda pendiente
cl1 = pd.read_excel(s1 / "03_INFORMACION_HOMOLOGADA/matriz_homologacion.xlsx", sheet_name="clasificacion_capas")
est = dict(zip(cl1.clave, cl1.estado))
check("sistema de referencia" in est["tratamientos_urb.shp::"], "Shapefile sin .prj queda pendiente por CRS (no se asume)")
check("equivalentes" in est["SUELO_MUNICIPAL_FINAL.gpkg::suelo_municipal"], "Capas equivalentes no se fusionan")
check(est["predios_catastro.shp::"].startswith("SIN CORRESPONDENCIA"), "Capa sin correspondencia se conserva")
val1 = pd.read_excel(s1 / "03_INFORMACION_HOMOLOGADA/matriz_homologacion.xlsx", sheet_name="valores_dominio")
zv = val1[val1.valor_origen == "Zona verde"]
check(len(zv) == 1 and zv.valor_homologado.isna().all(), "Valor sin correspondencia ('Zona verde') no se aproxima")
check((s1 / "01_INSUMOS_ORIGINALES/insumos/secretaria_planeacion/usos_urbanos.zip").exists(), "Originales conservados (incluido ZIP)")
# Pasada 2: estructura oficial
gpkg = next((s2 / "04_BASE_DATOS_LADM_COL_POT").glob("*.gpkg"))
capas = dict(pyogrio.list_layers(str(gpkg)))
for t, cols in cat.intermedia["tablas"].items():
    info = pyogrio.read_info(str(gpkg), layer=t)
    of = [c["nombre"] for c in cols if not c["geometria"]]
    check(list(info["fields"]) == of, f"{t}: columnas idénticas al script oficial 1")
    g = next((c for c in cols if c["geometria"]), None)
    if g:
        check(info["crs"] == "EPSG:9377" and info["geometry_name"] == g["nombre"], f"{t}: EPSG:9377 y columna '{g['nombre']}'")
val2 = pd.read_excel(s2 / "03_INFORMACION_HOMOLOGADA/matriz_homologacion.xlsx", sheet_name="valores_dominio")
ren = val2[val2.valor_origen == "Renovación urbana"]
check(len(ren) == 1 and ren.metodo.iloc[0] == "valor_no_hoja", "Valor de nodo no hoja queda pendiente con hijos sugeridos")
reg = pd.read_excel(s2 / "08_REPORTES/reportes_procesamiento.xlsx", sheet_name="reglas_evaluadas")
e = dict(zip(reg.id, reg.estado))
check(e.get("T6") == "FALLA", "Detecta superposición de tratamientos (T6)")
check(e.get("T10") == "FALLA", "Detecta vacío de áreas de actividad en suelo urbano (T10)")
check(e.get("G5") == "CON_ADVERTENCIAS", "Detecta suelo rural sin zonificar (G5)")
check(e.get("I1") == "NO_EJECUTADA", "INTERLIS se reporta NO EJECUTADA (no se simula)")
check(e.get("T17/TM1") == "CUMPLE" and e.get("T18") == "CUMPLE", "Centro poblado en suelo rural y coincidente con su zonificación")
check(any(p.name.endswith(".zip") for p in (s2 / "09_ENTREGA_FINAL").iterdir()), "ZIP de entrega generado")
print(f"\n{len(fallos)} fallas")
sys.exit(1 if fallos else 0)
