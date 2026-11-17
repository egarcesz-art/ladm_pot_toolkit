"""Genera un municipio SINTÉTICO con insumos desorganizados para probar el toolkit.

Contiene a propósito: nombres heterogéneos, varios formatos (SHP, GPKG, GeoJSON, KML, CSV, DXF, ZIP, XLSX,
GeoTIFF, PDF), distintos sistemas de referencia (EPSG:3116, 9377, 4326, sin .prj), una capa duplicada
(equivalente), una geometría inválida, valores no homologables y una capa sin correspondencia en el modelo.
NO representa ningún municipio real.
"""
import shutil
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point, Polygon, box

dest = Path(sys.argv[1] if len(sys.argv) > 1 else "insumos_prueba")
if dest.exists():
    shutil.rmtree(dest)
(dest / "cartografia_consultor").mkdir(parents=True)
(dest / "secretaria_planeacion").mkdir()
(dest / "riesgo").mkdir()
(dest / "documentos").mkdir()

X0, Y0 = 4_720_000, 2_250_000           # EPSG:9377 (zona centro-occidente, ficticia)
lim = box(X0, Y0, X0 + 10_000, Y0 + 10_000)
urb = box(X0 + 4_000, Y0 + 4_000, X0 + 6_000, Y0 + 6_000)
exp_ = box(X0 + 6_000, Y0 + 4_000, X0 + 7_000, Y0 + 6_000)
rural = lim.difference(urb).difference(exp_)
crs9377 = "EPSG:9377"

def g(data, geoms, crs=crs9377):
    return gpd.GeoDataFrame(data, geometry=geoms, crs=crs)

# Límite municipal (Shapefile, MAGNA-SIRGAS Bogotá EPSG:3116)
g({"MPIO_CCDGO": ["99999"], "MPIO_CNMBR": ["MUNICIPIO SINTETICO"]}, [lim]).to_crs(3116).to_file(dest / "secretaria_planeacion/Limite_Mpio.shp")

# Clasificación del suelo (SHP 3116) con valor 'Expansión' (tilde) y fenómeno de protección mezclado
g({"CLASE": ["Urbano", "Expansión urbana", "Rural"], "AREA_HA": [400.0, 200.0, 9400.0], "ACUERDO": ["Acuerdo 012 de 2000"] * 3},
  [urb, exp_, rural]).to_crs(3116).to_file(dest / "cartografia_consultor/CLASIFICACION_SUELO.shp")

# Capa equivalente (misma temática, otro nombre, otro CRS, valores en mayúsculas) -> no debe fusionarse
g({"TIPO": ["URBANO", "EXPANSION URBANA", "RURAL"]}, [urb.buffer(2), exp_, rural]).to_file(dest / "secretaria_planeacion/SUELO_MUNICIPAL_FINAL.gpkg", layer="suelo_municipal")

# Zonificación rural (GeoJSON WGS84) con polígono inválido (moño) y valor no homologable
cp_geom = box(X0 + 1_000, Y0 + 8_000, X0 + 1_600, Y0 + 8_600)
z1 = box(X0, Y0, X0 + 4_000, Y0 + 10_000).difference(cp_geom)
z2 = box(X0 + 4_000, Y0, X0 + 10_000, Y0 + 4_000)
z3 = Polygon([(X0 + 4_000, Y0 + 6_000), (X0 + 10_000, Y0 + 10_000), (X0 + 10_000, Y0 + 6_000), (X0 + 4_000, Y0 + 10_000)])  # moño inválido
z4 = box(X0 + 7_000, Y0 + 4_000, X0 + 10_000, Y0 + 6_000)
zr = g({"CATEGORIA": ["Agropecuario", "Areas SINAP", "Forestal", "Ganadería extensiva", "Centro poblado rural"],
        "USO_PPAL": ["Agrícola", "Preservación", "Forestal", "Pecuario", "Centro poblado"],
        "NOMBRE_ZONA": ["Zona agrícola norte", "Reserva El Alto", "Zona forestal", "Zona ganadera", "CP La Esperanza"],
        "USO_COMPATIBLE": ["Pecuario", "Investigación", "Agroforestal", "Agrícola", "Residencial"],
        "USO_CONDICIONADO": ["Vivienda campestre", "Ecoturismo", "Turismo", "Turismo", "Comercio"],
        "USO_PROHIBIDO": ["Minería", "Agropecuario", "Minería", "Industria", "Industria"],
        "RESTRICCION": ["Acuerdo 012/2000 art. 50"] * 5},
       [z1, z2, z3, z4, cp_geom])
zr.to_crs(4326).to_file(dest / "cartografia_consultor/zonificacion_rural_EOT.geojson", driver="GeoJSON")

# Centros poblados (SHP 3116)
g({"NOMBRE": ["La Esperanza"], "COD_CP": ["99999001"]}, [cp_geom]).to_crs(3116).to_file(dest / "cartografia_consultor/centros_poblados.shp")

# Tratamientos (SHP SIN .prj -> CRS no declarado)
tu = g({"TRATAMIENTO": ["Consolidación", "Desarrollo", "Renovación urbana"], "RESTRICCION": ["Norma 1", "Norma 2", "Norma 3"]},
       [box(X0 + 4_000, Y0 + 4_000, X0 + 5_000, Y0 + 6_000), box(X0 + 5_000, Y0 + 4_000, X0 + 7_000, Y0 + 6_000), box(X0 + 4_500, Y0 + 5_500, X0 + 5_200, Y0 + 6_000)])
tu.to_file(dest / "cartografia_consultor/tratamientos_urb.shp")
(dest / "cartografia_consultor/tratamientos_urb.prj").unlink()

# Áreas de actividad dentro de un ZIP (SHP 3116); 'Zona verde' no está en el dominio
tmp = dest / "_tmp_aa"
tmp.mkdir()
g({"USO": ["Residencial", "Comercial", "Mixto", "Zona verde"], "ZONA": ["ZR-1", "ZC-1", "ZM-1", "ZV-1"],
   "USO_COMPATIBLE": ["Comercio barrial"] * 4, "USO_CONDICIONADO": ["Talleres"] * 4, "USO_PROHIBIDO": ["Industria pesada"] * 4,
   "RESTRICCION": ["Ficha normativa"] * 4},
  [box(X0 + 4_000, Y0 + 4_000, X0 + 5_000, Y0 + 5_000), box(X0 + 5_000, Y0 + 4_000, X0 + 6_000, Y0 + 5_000),
   box(X0 + 4_000, Y0 + 5_000, X0 + 5_000, Y0 + 6_000), box(X0 + 5_000, Y0 + 5_000, X0 + 5_900, Y0 + 6_000)]
  ).to_crs(3116).to_file(tmp / "AREAS_ACTIVIDAD_URBANA.shp")
with zipfile.ZipFile(dest / "secretaria_planeacion/usos_urbanos.zip", "w") as z:
    for p in tmp.iterdir():
        z.write(p, p.name)
shutil.rmtree(tmp)

# Amenazas: movimientos en masa (SHP 3116, sin campo de fenómeno) e inundación (KML)
g({"CATEGORIA": ["Alta", "Media", "Baja"], "RESTRICCION": ["Restricción"] * 3},
  [box(X0, Y0 + 7_000, X0 + 3_000, Y0 + 10_000), box(X0, Y0 + 3_000, X0 + 3_000, Y0 + 7_000), box(X0, Y0, X0 + 3_000, Y0 + 3_000)]
  ).to_crs(3116).to_file(dest / "riesgo/AMENAZA_MOV_MASA.shp")
g({"Name": ["Inundación alta"], "NIVEL": ["ALTA"], "FENOMENO": ["Inundación"], "RESTRICCION": ["Ronda"]},
  [box(X0 + 6_000, Y0 + 1_000, X0 + 9_000, Y0 + 1_500)]).to_crs(4326).to_file(dest / "riesgo/amenaza_inundacion.kml", driver="KML")

# Equipamientos (CSV con X/Y en EPSG:3116, sin CRS declarado)
pts = gpd.GeoSeries([Point(X0 + 4_500, Y0 + 4_500), Point(X0 + 5_500, Y0 + 5_500), Point(X0 + 1_300, Y0 + 8_300)], crs=crs9377).to_crs(3116)
pd.DataFrame({"NOMBRE": ["Escuela Central", "Hospital", "Escuela rural"], "TIPO_EQUIPAMIENTO": ["Educacion", "Salud", "Educacion"],
              "NIVEL": ["Municipal", "Municipal", "Local"], "ESTADO": ["Existente", "Existente", "Proyectado"],
              "X": pts.x.round(2), "Y": pts.y.round(2), "RESTRICCION": ["Equipamiento"] * 3}
             ).to_csv(dest / "cartografia_consultor/equipamientos_coordenadas.csv", index=False)

# Vías en DXF (sin CRS)
g({"Layer": ["VIA_SEGUNDO_ORDEN", "VIA_TERCER_ORDEN"]},
  [LineString([(X0, Y0 + 5_000), (X0 + 10_000, Y0 + 5_000)]), LineString([(X0 + 5_000, Y0), (X0 + 5_000, Y0 + 4_000)])]
  ).to_file(dest / "cartografia_consultor/red_vial.dxf", driver="DXF")

# Capa sin correspondencia en el modelo
g({"NPN": ["999990001", "999990002"], "AVALUO": [1e8, 2e8]}, [box(X0 + 4_100, Y0 + 4_100, X0 + 4_200, Y0 + 4_200), box(X0 + 4_300, Y0 + 4_100, X0 + 4_400, Y0 + 4_200)]
  ).to_file(dest / "secretaria_planeacion/predios_catastro.shp")

# Alfanumérico, ráster y documento
pd.DataFrame({"ZONA": ["ZR-1", "ZC-1"], "ALTURA_MAX": [3, 5], "IO": [0.7, 0.8]}).to_excel(dest / "secretaria_planeacion/fichas_normativas.xlsx", index=False)
import rasterio
from rasterio.transform import from_origin
dem = (1500 + 50 * np.random.default_rng(1).random((100, 100))).astype("float32")
with rasterio.open(dest / "cartografia_consultor/DEM_12m.tif", "w", driver="GTiff", height=100, width=100, count=1, dtype="float32",
                   crs="EPSG:9377", transform=from_origin(X0, Y0 + 10_000, 100, 100)) as r:
    r.write(dem, 1)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig = plt.figure(figsize=(8.5, 11)); fig.text(0.1, 0.9, "ACUERDO 012 DE 2000 (documento sintético de prueba)"); fig.savefig(dest / "documentos/Acuerdo_EOT.pdf"); plt.close(fig)
print(f"Insumos sintéticos en {dest.resolve()}")
