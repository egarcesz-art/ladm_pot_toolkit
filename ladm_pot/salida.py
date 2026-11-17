"""Construcción de la base de datos intermedia, reportes, carpeta de entrega y ZIP."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import shutil
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from .modelo import Catalogo

log = logging.getLogger("ladm_pot")

CARPETAS = ["01_INSUMOS_ORIGINALES", "02_INVENTARIO_CARTOGRAFICO", "03_INFORMACION_HOMOLOGADA", "04_BASE_DATOS_LADM_COL_POT",
            "05_CARTOGRAFIA_TEMATICA", "06_DOCUMENTACION_TECNICA", "07_VALIDACIONES", "08_REPORTES", "09_ENTREGA_FINAL"]

COLOR_SEV = {"CRÍTICO": "F8CBAD", "ALTO": "FCE4D6", "MEDIO": "FFF2CC", "BAJO": "E2EFDA"}


def crear_estructura(raiz: Path) -> dict[str, Path]:
    rutas = {}
    for c in CARPETAS:
        (raiz / c).mkdir(parents=True, exist_ok=True)
        rutas[c[:2]] = raiz / c
    return rutas


def excel(path: Path, hojas: dict[str, pd.DataFrame]):
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        for nombre, df in hojas.items():
            (df if len(df.columns) else pd.DataFrame({"(sin datos)": []})).to_excel(w, sheet_name=nombre[:31], index=False)
    wb = load_workbook(path)
    for ws in wb.worksheets:
        ws.freeze_panes = "A2"
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F4E78")
            c.alignment = Alignment(wrap_text=True, vertical="center")
        for col in ws.columns:
            largo = max((len(str(c.value)) if c.value is not None else 0) for c in list(col)[:300])
            ws.column_dimensions[col[0].column_letter].width = min(max(10, largo + 2), 70)
        enc = [c.value for c in ws[1]]
        if "severidad" in enc:
            k = enc.index("severidad") + 1
            for fila in ws.iter_rows(min_row=2):
                color = COLOR_SEV.get(fila[k - 1].value)
                if color:
                    for c in fila:
                        c.fill = PatternFill("solid", fgColor=color)
    wb.save(path)


def escribir_gpkg_intermedio(path: Path, tablas: dict[str, gpd.GeoDataFrame], municipio: pd.DataFrame, cat: Catalogo,
                             trazabilidad: pd.DataFrame):
    if path.exists():
        path.unlink()
    for t, cols in cat.intermedia["tablas"].items():
        nombres = [c["nombre"] for c in cols]
        if t == "municipio":
            df = municipio.reindex(columns=nombres)
            pyogrio.write_dataframe(df.astype(object).where(df.notna(), None), str(path), layer=t)
            continue
        gcol = next(c for c in cols if c["geometria"])
        g = tablas.get(t)
        atributos = [n for n in nombres if n != gcol["nombre"]]
        if g is None or len(g) == 0:
            g = gpd.GeoDataFrame(columns=atributos, geometry=gpd.GeoSeries([], crs=cat.srid), crs=cat.srid)
        g = g.reindex(columns=atributos + ["geometry"])
        for c in cols:
            if c["nombre"] in g.columns and not c["geometria"]:
                if "date" in c["tipo_sql"].lower():
                    g[c["nombre"]] = pd.to_datetime(g[c["nombre"]], errors="coerce").dt.date
                elif "numeric" in c["tipo_sql"].lower():
                    g[c["nombre"]] = pd.to_numeric(g[c["nombre"]], errors="coerce")
                else:
                    g[c["nombre"]] = g[c["nombre"]].astype(object).where(g[c["nombre"]].notna(), None)
        g = gpd.GeoDataFrame(g, geometry="geometry", crs=cat.srid).rename_geometry(gcol["nombre"])
        tipo = {"multipolygonz": "MultiPolygon Z", "linestringz": "LineString Z", "pointz": "Point Z"}[gcol["geometria"]]
        pyogrio.write_dataframe(g, str(path), layer=t, geometry_type=tipo, append=False,
                                layer_options={"GEOMETRY_NAME": gcol["nombre"]})
    pyogrio.write_dataframe(trazabilidad, str(path), layer="zz_trazabilidad_origen")


def guion_fase4(carpeta: Path, cat: Catalogo, nombre_gpkg: str):
    """Scripts para completar la migración oficial (PostGIS + ETL oficial + XTF + ilivalidator)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    tablas = [t for t in cat.intermedia["tablas"]]
    cargas = "\n".join(
        f'ogr2ogr -f PostgreSQL "$PG" "$GPKG" {t} -nln data_intermedia.{t} -append -dim XYZ'
        + (" -nlt PROMOTE_TO_MULTI" if any(c["geometria"] == "multipolygonz" for c in cat.intermedia["tablas"][t]) else "")
        for t in tablas)
    (carpeta / "1_cargar_estructura_intermedia_postgis.sh").write_text(f"""#!/usr/bin/env bash
# Carga la estructura intermedia (GeoPackage) en PostgreSQL/PostGIS.
# Requisitos: PostgreSQL + PostGIS, GDAL (ogr2ogr), psql. Ajuste la conexión.
set -euo pipefail
PG="PG:host=localhost port=5432 dbname=pot user=postgres password=CAMBIAR"
PSQL="psql -h localhost -p 5432 -U postgres -d pot"
GPKG="$(dirname "$0")/../{nombre_gpkg}"
MODELO="$(dirname "$0")/../../06_DOCUMENTACION_TECNICA/modelo_oficial_usado"

# 1) Crear el esquema data_intermedia con el SCRIPT OFICIAL (tipos y NOT NULL oficiales)
$PSQL -f "$MODELO/ESTRUCTURA_INTERMEDIA/1_create_intermediate_structure.sql"

# 2) Cargar los datos homologados en las tablas oficiales
{cargas}

# 3) Validaciones oficiales de dominio (requiere el esquema ladm_pot creado, ver paso 4 del README)
# $PSQL -f "$MODELO/ESTRUCTURA_INTERMEDIA/2_validate_intermediate_structure_data.sql"
""", encoding="utf-8")
    req = "\n".join(f"  ('{t}')," for t in cat.tablas_etl).rstrip(",")
    (carpeta / "2_verificar_esquema_ladm_pot.sql").write_text(f"""-- Comprueba que el esquema ladm_pot (creado con ili2pg / QGIS Model Baker a partir de
-- modelo_oficial_usado/*.ili) tiene las tablas que espera el ETL oficial (script 4).
-- Lista extraída automáticamente del script 4_etl_intermediate_structure_to_ladm_col_pot.sql
with esperadas(tabla) as (values
{req}
)
select e.tabla as tabla_faltante
from esperadas e
left join information_schema.tables t on t.table_schema = 'ladm_pot' and t.table_name = e.tabla
where t.table_name is null;
-- Si la consulta no devuelve filas, el esquema es compatible con el ETL oficial.
""", encoding="utf-8")
    (carpeta / "LEAME_FASE4.md").write_text(f"""# Fase 4 – Migración al modelo LADM_COL-POT y generación del XTF

La guía oficial de migración del MVCT define la ruta: estructura intermedia → ETL → modelo LADM_COL-POT → archivo XTF.
Este toolkit entrega la estructura intermedia oficial homologada (`{nombre_gpkg}`). Los pasos siguientes
requieren PostgreSQL/PostGIS y Java (no disponibles en el entorno donde se generó este paquete).

1. `1_cargar_estructura_intermedia_postgis.sh` – crea `data_intermedia` con el script oficial 1 y carga los datos.
2. Crear el esquema `ladm_pot` importando el modelo `LADM_COL_v_2_0_0_Ext_POT` (carpeta `06_DOCUMENTACION_TECNICA/modelo_oficial_usado`) con
   QGIS Model Baker o ili2pg (`--schemaimport --dbschema ladm_pot --models LADM_COL_v_2_0_0_Ext_POT --modeldir <carpeta>`
   más los parámetros de su flujo institucional; **verifique los parámetros con la documentación de ili2db/Model Baker**).
3. Ejecutar `2_verificar_esquema_ladm_pot.sql`: debe devolver 0 filas ({len(cat.tablas_etl)} tablas esperadas por el ETL).
4. Ejecutar los scripts oficiales 2 (validación de dominios), 3 (identificadores) y 4 (ETL) de `ESTRUCTURA_INTERMEDIA`.
5. Exportar el XTF: `java -jar ili2pg.jar --export --dbhost ... --dbdatabase ... --dbusr ... --dbpwd ... --dbschema ladm_pot --models LADM_COL_v_2_0_0_Ext_POT --modeldir <carpeta> entrega.xtf`
6. Validar: `java -jar ilivalidator.jar --modeldir <carpeta> --log validacion_xtf.log entrega.xtf`
7. Ejecutar los validadores oficiales `VALIDADORES/SQL/*.sql` sobre `ladm_pot`.

Hasta completar los pasos 5–6 la validación INTERLIS figura como **NO EJECUTADA** en los reportes.
""", encoding="utf-8")


def vistas_previas(carpeta: Path, tablas: dict[str, gpd.GeoDataFrame], limite):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tematicas = {
        "01_Componente_general_Clasificacion_suelo": ("clasificacion_suelo", "tipo_clasificacion_suelo"),
        "02_Componente_rural_Zonificacion_suelo_rural": ("zonificacion_suelo_rural", "tipo_categoria_rural"),
        "03_Componente_urbano_Areas_actividad": ("areas_actividad", "uso_principal"),
        "04_Componente_urbano_Tratamientos": ("tratamiento_urbanistico", "tipo_tratamiento_urbanistico"),
        "05_Componente_urbano_Suelo_proteccion": ("suelo_proteccion_urbano", "uso_principal"),
        "06_Centros_poblados": ("centro_poblado_rural", "nombre"),
        "07_Amenazas_Zonificacion": ("zonificacion_amenaza", "categoria_amenaza"),
        "08_Amenazas_Areas_condicion_amenaza": ("area_condicion_amenaza", "fenomeno"),
        "09_Riesgo_Areas_condicion_riesgo": ("area_condicion_riesgo", "fenomeno"),
        "10_Sistemas_generales": (("sistemas_generales_poligono", "sistemas_generales_linea", "sistemas_generales_punto"), "tipo_sistema_general"),
    }
    hechos = []
    for nombre, (t, campo) in tematicas.items():
        partes = [tablas.get(x) for x in (t if isinstance(t, tuple) else (t,))]
        partes = [p for p in partes if p is not None and len(p)]
        if not partes:
            continue
        fig, ax = plt.subplots(figsize=(10, 10))
        if limite is not None and len(limite):
            limite.boundary.plot(ax=ax, color="black", linewidth=0.8)
        for p in partes:
            p.plot(ax=ax, column=campo if p[campo].notna().any() else None, legend=True, categorical=True, alpha=0.75,
                   edgecolor="0.3", linewidth=0.3, missing_kwds={"color": "lightgrey", "label": "Sin homologar"},
                   legend_kwds={"fontsize": 7, "loc": "lower left"})
        ax.set_title(f"{nombre.replace('_', ' ')}\nVista de control (no es cartografía oficial) – EPSG:9377", fontsize=10)
        ax.set_axis_off()
        fig.savefig(carpeta / f"{nombre}.png", dpi=110, bbox_inches="tight")
        plt.close(fig)
        sub = gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), crs=partes[0].crs)
        sub.to_file(carpeta / "cartografia_tematica_control.gpkg", layer=nombre, engine="pyogrio")
        hechos.append(nombre)
    return hechos


def manifiesto(raiz: Path) -> pd.DataFrame:
    filas = []
    for p in sorted(raiz.rglob("*")):
        if p.is_file():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            filas.append({"ruta": str(p.relative_to(raiz)), "bytes": p.stat().st_size, "sha256": h})
    return pd.DataFrame(filas)


def comprimir(raiz: Path, destino_zip: Path):
    if destino_zip.exists():
        destino_zip.unlink()
    with zipfile.ZipFile(destino_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(raiz.rglob("*")):
            if p.is_file() and p.resolve() != destino_zip.resolve():
                z.write(p, Path(raiz.name) / p.relative_to(raiz))


def copiar_modelo(cat: Catalogo, destino: Path):
    shutil.copytree(cat.carpeta, destino, dirs_exist_ok=True)


def informe_md(path: Path, ctx: dict) -> str:
    r = ctx
    res = r["resumen_cumplimiento"]
    tabla_cumpl = "\n".join(
        f"| {f.componente} | {f.reglas_evaluadas} | {f.cumplen} | {f.con_advertencias} | {f.fallan} | {f.no_ejecutadas} | {f.sin_datos} | "
        f"{'' if pd.isna(f.porcentaje_cumplimiento_reglas_evaluadas) else f'{f.porcentaje_cumplimiento_reglas_evaluadas} %'} |"
        for f in res.itertuples())
    sev = r["severidades"]
    capas_tabla = "\n".join(f"| {k} | {v} |" for k, v in r["registros_por_tabla"].items())
    pend = "\n".join(f"- {p}" for p in r["pendientes"][:60]) or "- Ninguno"
    texto = f"""# Informe general de procesamiento LADM_COL-POT

**Municipio:** {r['municipio']} ({r['departamento']}) – código DANE {r['dane']}
**Instrumento:** {r['instrumento']}
**Modelo:** {r['modelo']}
**Fecha de procesamiento:** {r['fecha']}
**Datos de prueba:** {'SÍ – este paquete se generó con datos SINTÉTICOS de prueba' if r.get('prueba') else 'No'}

> Este informe distingue entre *procesamiento* y *conformidad*. El porcentaje se calcula solo sobre reglas
> efectivamente evaluadas; las reglas no ejecutadas o sin datos se listan aparte. **Ningún resultado de este
> paquete equivale a la validación oficial del XTF**, que requiere la fase 4 (PostGIS + ETL oficial + ilivalidator).

## 1. Cifras del procesamiento

| Indicador | Valor |
|---|---|
| Archivos recibidos | {r['n_archivos']} |
| Capas/tablas/documentos identificados | {r['n_capas']} |
| Capas vectoriales | {r['n_vectoriales']} |
| Capas clasificadas en una tabla del modelo | {r['n_clasificadas']} |
| Capas homologadas y cargadas en la estructura intermedia | {r['n_cargadas']} |
| Capas pendientes de decisión (CRS, destino, equivalencias) | {r['n_pendientes_capa']} |
| Tablas de la estructura intermedia con datos | {r['n_tablas_con_datos']} de {r['n_tablas']} |
| Observaciones CRÍTICAS | {sev.get('CRÍTICO', 0)} |
| Observaciones ALTAS | {sev.get('ALTO', 0)} |
| Observaciones MEDIAS | {sev.get('MEDIO', 0)} |
| Observaciones BAJAS | {sev.get('BAJO', 0)} |

## 2. Registros cargados por tabla de la estructura intermedia

| Tabla | Registros |
|---|---|
{capas_tabla}

## 3. Cumplimiento por componente (sobre reglas evaluadas)

| Componente | Evaluadas | Cumplen | Con advertencias | Fallan | No ejecutadas | Sin datos | % cumplimiento |
|---|---|---|---|---|---|---|---|
{tabla_cumpl}

## 4. Pendientes que requieren decisión técnica

{pend}

Las decisiones se registran en `decisiones.json` (plantilla en `08_REPORTES/decisiones_pendientes.json`) y se
vuelve a ejecutar el proceso.

## 5. Limitaciones

{chr(10).join('- ' + l for l in r['limitaciones'])}
"""
    path.write_text(texto, encoding="utf-8")
    try:
        import markdown  # type: ignore
        html = markdown.markdown(texto, extensions=["tables"])
    except Exception:  # noqa: BLE001
        html = "<pre>" + texto.replace("<", "&lt;") + "</pre>"
    path.with_suffix(".html").write_text(
        "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'><title>Informe LADM_COL-POT</title>"
        "<style>body{font-family:system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;line-height:1.5}"
        "table{border-collapse:collapse;margin:1rem 0}td,th{border:1px solid #ccc;padding:.3rem .6rem}th{background:#1F4E78;color:#fff}"
        "blockquote{background:#FFF2CC;margin:0;padding:.5rem 1rem;border-left:4px solid #E0B000}</style></head><body>"
        + html + "</body></html>", encoding="utf-8")
    return texto
