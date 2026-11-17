"""Fase 1 – Recepción e inventario automático de insumos."""
from __future__ import annotations

import logging
import re
import shutil
import warnings
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

from .modelo import normalizar

log = logging.getLogger("ladm_pot")
warnings.filterwarnings("ignore", category=RuntimeWarning)

EXT_VECTOR = {".shp", ".gpkg", ".geojson", ".json", ".dxf", ".kml", ".gml", ".sqlite"}
EXT_TABLA = {".xlsx", ".xls", ".csv", ".txt", ".ods"}
EXT_RASTER = {".tif", ".tiff", ".img", ".asc", ".jp2", ".ecw", ".vrt"}
EXT_DOC = {".pdf", ".doc", ".docx", ".odt", ".pptx", ".dwg", ".qgz", ".qgs", ".mxd", ".aprx", ".xml", ".md"}
COMPONENTES_SHP = {".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".qix", ".qmd", ".xml"}

NOMBRES_X = {"X", "ESTE", "COORD_X", "COORDX", "LONGITUD", "LON", "LONG", "LNG", "EASTING", "X_COORD"}
NOMBRES_Y = {"Y", "NORTE", "COORD_Y", "COORDY", "LATITUD", "LAT", "NORTHING", "Y_COORD"}


def extraer_comprimidos(carpeta: Path, destino: Path) -> list[dict]:
    """Extrae ZIP/KMZ a una carpeta de trabajo (los originales no se tocan)."""
    eventos = []
    for z in sorted(list(carpeta.rglob("*.zip")) + list(carpeta.rglob("*.kmz"))):
        out = destino / (z.stem + ("_kmz" if z.suffix.lower() == ".kmz" else ""))
        try:
            with zipfile.ZipFile(z) as zf:
                for miembro in zf.namelist():
                    p = (out / miembro).resolve()
                    if not str(p).startswith(str(out.resolve())):
                        raise ValueError(f"Ruta insegura dentro del ZIP: {miembro}")
                zf.extractall(out)
            eventos.append({"archivo": str(z), "estado": "extraído", "destino": str(out)})
        except Exception as e:  # noqa: BLE001
            eventos.append({"archivo": str(z), "estado": f"error: {e}", "destino": ""})
    # ZIP anidados (un nivel)
    for z in sorted(destino.rglob("*.zip")):
        out = z.parent / z.stem
        if not out.exists():
            try:
                with zipfile.ZipFile(z) as zf:
                    zf.extractall(out)
                eventos.append({"archivo": str(z), "estado": "extraído (anidado)", "destino": str(out)})
            except Exception as e:  # noqa: BLE001
                eventos.append({"archivo": str(z), "estado": f"error: {e}", "destino": ""})
    return eventos


def _epsg(crs) -> int | None:
    if crs is None:
        return None
    try:
        e = crs.to_epsg(min_confidence=70)
        return int(e) if e else None
    except Exception:  # noqa: BLE001
        return None


def sugerir_crs(bounds) -> str:
    """Solo SUGIERE (nunca asigna) a partir del rango de coordenadas."""
    if bounds is None or any(pd.isna(b) for b in bounds):
        return ""
    minx, miny, maxx, maxy = bounds
    if -82 <= minx <= -66 and -5 <= miny <= 14 and -82 <= maxx <= -66:
        return "Coordenadas geográficas (grados): posible EPSG:4686 (MAGNA-SIRGAS) o EPSG:4326 (WGS84)"
    if 3_900_000 <= minx <= 6_000_000 and 1_000_000 <= miny <= 3_200_000:
        return "Rango compatible con EPSG:9377 (MAGNA-SIRGAS / Origen-Nacional)"
    if 500_000 <= minx <= 1_600_000 and 500_000 <= miny <= 1_900_000:
        return "Rango compatible con MAGNA-SIRGAS Gauss-Krüger (EPSG:3114–3118); el origen exacto (Oeste, Bogotá, etc.) no se puede deducir"
    return "No reconocible"


def _resumen_campos(df: pd.DataFrame) -> list[dict]:
    out = []
    for c in df.columns:
        if c == "geometry":
            continue
        s = df[c]
        try:
            unicos = s.dropna().astype(str).unique()
        except Exception:  # noqa: BLE001
            unicos = np.array([])
        out.append({
            "campo": c,
            "tipo": str(s.dtype),
            "n_nulos": int(s.isna().sum() + (s.astype(str).str.strip() == "").sum() if (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)) else s.isna().sum()),
            "n_unicos": int(len(unicos)),
            "muestra": "; ".join(map(str, unicos[:12])),
        })
    return out


def leer_vector(ruta: str, capa: str | None) -> gpd.GeoDataFrame:
    return gpd.read_file(ruta, layer=capa, engine="pyogrio") if capa else gpd.read_file(ruta, engine="pyogrio")


def _csv_a_puntos(df: pd.DataFrame):
    norm = {normalizar(c): c for c in df.columns}
    cx = next((norm[n] for n in norm if n in NOMBRES_X), None)
    cy = next((norm[n] for n in norm if n in NOMBRES_Y), None)
    if not cx or not cy:
        return None, None
    x = pd.to_numeric(df[cx].astype(str).str.replace(",", "."), errors="coerce")
    y = pd.to_numeric(df[cy].astype(str).str.replace(",", "."), errors="coerce")
    if x.notna().mean() < 0.8:
        return None, None
    g = gpd.GeoDataFrame(df.copy(), geometry=gpd.points_from_xy(x, y), crs=None)
    return g, f"{cx}/{cy}"


def _calidad_geometrica(g: gpd.GeoDataFrame) -> dict:
    geom = g.geometry
    vacias = int((geom.isna() | geom.is_empty).sum())
    validas = geom[~(geom.isna() | geom.is_empty)]
    invalidas = int((~validas.is_valid).sum()) if len(validas) else 0
    try:
        wkb = validas.to_wkb()
        duplicados = int(wkb.duplicated().sum())
    except Exception:  # noqa: BLE001
        duplicados = -1
    multipartes = int((shapely.get_num_geometries(validas.values) > 1).sum()) if len(validas) else 0
    tipos = ", ".join(sorted(validas.geom_type.unique())) if len(validas) else ""
    return {"geom_vacias": vacias, "geom_invalidas": invalidas, "geom_duplicadas": duplicados,
            "multipartes": multipartes, "tipos_geometria": tipos}


def inventariar(carpetas: list[Path]) -> tuple[list[dict], list[dict]]:
    """Devuelve (capas, archivos). `capas` incluye vectores, tablas, rásteres y documentos."""
    capas, archivos = [], []
    vistos = set()
    for carpeta in carpetas:
        for p in sorted(carpeta.rglob("*")):
            if p.is_dir():
                if p.suffix.lower() == ".gdb" and p not in vistos:
                    vistos.add(p)
                    capas += _inventariar_vector(p, "Geodatabase (.gdb)")
                continue
            if any(parent.suffix.lower() == ".gdb" for parent in p.parents):
                continue
            ext = p.suffix.lower()
            archivos.append({"archivo": p.name, "ruta": str(p), "extension": ext, "bytes": p.stat().st_size})
            if ext in (".zip", ".kmz") or ext in COMPONENTES_SHP:
                continue
            try:
                if ext in EXT_VECTOR:
                    capas += _inventariar_vector(p, {".shp": "Shapefile", ".gpkg": "GeoPackage", ".geojson": "GeoJSON",
                                                    ".json": "GeoJSON", ".dxf": "DXF", ".kml": "KML", ".gml": "GML",
                                                    ".sqlite": "SpatiaLite"}[ext])
                elif ext in EXT_TABLA:
                    capas += _inventariar_tabla(p)
                elif ext in EXT_RASTER:
                    capas.append(_inventariar_raster(p))
                elif ext in EXT_DOC:
                    capas.append(_inventariar_documento(p))
                else:
                    capas.append({"id": None, "archivo": p.name, "ruta": str(p), "capa": "", "formato": ext or "sin extensión",
                                  "categoria": "no_reconocido", "observacion": "Formato no reconocido; se conserva en insumos originales"})
            except Exception as e:  # noqa: BLE001
                log.exception("Error inventariando %s", p)
                capas.append({"id": None, "archivo": p.name, "ruta": str(p), "capa": "", "formato": ext,
                              "categoria": "error_lectura", "observacion": f"No se pudo leer: {e}"})
    # shapefiles sin .prj / componentes faltantes
    for c in capas:
        if c.get("formato") == "Shapefile":
            base = Path(c["ruta"]).with_suffix("")
            faltan = [e for e in (".shx", ".dbf", ".prj") if not base.with_suffix(e).exists() and not base.with_suffix(e.upper()).exists()]
            if faltan:
                c["observacion"] = (c.get("observacion", "") + f" Faltan componentes: {', '.join(faltan)}.").strip()
    for i, c in enumerate(capas, 1):
        c["id"] = f"C{i:03d}"
    return capas, archivos


def _inventariar_vector(p: Path, formato: str) -> list[dict]:
    out = []
    try:
        listado = pyogrio.list_layers(str(p))
    except Exception as e:  # noqa: BLE001
        return [{"archivo": p.name, "ruta": str(p), "capa": "", "formato": formato, "categoria": "error_lectura",
                 "observacion": f"No se pudo abrir: {e}"}]
    for nombre_capa, tipo_geom in listado:
        capa = nombre_capa if len(listado) > 1 or formato in ("Geodatabase (.gdb)", "GeoPackage", "DXF", "KML", "GML", "SpatiaLite") else None
        try:
            g = leer_vector(str(p), capa)
        except Exception as e:  # noqa: BLE001
            out.append({"archivo": p.name, "ruta": str(p), "capa": nombre_capa, "formato": formato,
                        "categoria": "error_lectura", "observacion": f"Error de lectura: {e}"})
            continue
        es_espacial = isinstance(g, gpd.GeoDataFrame) and g.geometry.notna().any()
        crs = g.crs if es_espacial else None
        bounds = tuple(g.total_bounds) if es_espacial and len(g) else None
        info = {
            "archivo": p.name, "ruta": str(p), "capa": nombre_capa if capa else "", "formato": formato,
            "categoria": "vector" if es_espacial else "tabla",
            "n_registros": int(len(g)),
            "crs": crs.name if crs else "", "epsg": _epsg(crs),
            "crs_wkt": crs.to_wkt() if crs else "",
            "bbox": ", ".join(f"{b:.4f}" for b in bounds) if bounds else "",
            "sugerencia_crs": "" if crs else sugerir_crs(bounds),
            "campos": _resumen_campos(g),
            "n_registros_duplicados_atributos": int(pd.DataFrame(g.drop(columns="geometry", errors="ignore")).astype(str).duplicated().sum()) if len(g) else 0,
            "fuente_procedencia": p.parent.name,
            "observacion": "",
        }
        if formato in ("KML",) and crs is None:
            info["observacion"] += " KML: por especificación OGC usa WGS84 (EPSG:4326)."
        if es_espacial:
            info.update(_calidad_geometrica(g))
        out.append(info)
    return out


def _inventariar_tabla(p: Path) -> list[dict]:
    out = []
    if p.suffix.lower() in (".csv", ".txt"):
        try:
            df = pd.read_csv(p, sep=None, engine="python", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(p, sep=None, engine="python", encoding="latin-1")
        hojas = {"": df}
    else:
        hojas = pd.read_excel(p, sheet_name=None)
    for hoja, df in hojas.items():
        g, cols = _csv_a_puntos(df) if p.suffix.lower() in (".csv", ".txt") else (None, None)
        info = {"archivo": p.name, "ruta": str(p), "capa": hoja, "formato": p.suffix.lower().lstrip(".").upper(),
                "categoria": "tabla", "n_registros": int(len(df)), "campos": _resumen_campos(df),
                "n_registros_duplicados_atributos": int(df.astype(str).duplicated().sum()),
                "fuente_procedencia": p.parent.name, "observacion": ""}
        if g is not None:
            info.update({"categoria": "vector", "formato": "CSV con coordenadas", "crs": "", "epsg": None, "crs_wkt": "",
                         "bbox": ", ".join(f"{b:.4f}" for b in g.total_bounds), "sugerencia_crs": sugerir_crs(tuple(g.total_bounds)),
                         "observacion": f"Coordenadas detectadas en {cols}; el CSV no declara sistema de referencia."})
            info.update(_calidad_geometrica(g))
        out.append(info)
    return out


def _inventariar_raster(p: Path) -> dict:
    import rasterio
    with rasterio.open(p) as r:
        crs = r.crs
        epsg = None
        try:
            epsg = crs.to_epsg() if crs else None
        except Exception:  # noqa: BLE001
            pass
        nombre = normalizar(p.stem)
        es_dem = r.count == 1 and any(k in nombre for k in ("DEM", "MDT", "MDE", "DTM", "DSM", "ELEV", "ALOS", "SRTM"))
        return {"archivo": p.name, "ruta": str(p), "capa": "", "formato": f"Ráster ({r.driver})", "categoria": "raster",
                "n_registros": r.count, "crs": crs.to_string() if crs else "", "epsg": epsg, "crs_wkt": crs.to_wkt() if crs else "",
                "bbox": ", ".join(f"{b:.4f}" for b in r.bounds), "sugerencia_crs": "" if crs else sugerir_crs(tuple(r.bounds)),
                "resolucion": f"{r.res[0]:.4f} x {r.res[1]:.4f}", "tipos_geometria": f"{r.count} banda(s) {r.dtypes[0]}",
                "observacion": ("Posible modelo de elevación (DEM/MDT). " if es_dem else "") +
                               "Los rásteres no forman parte de la estructura intermedia LADM_COL-POT; se inventarían como insumo.",
                "fuente_procedencia": p.parent.name, "campos": []}


def _inventariar_documento(p: Path) -> dict:
    obs, paginas = "", None
    if p.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            paginas = len(PdfReader(str(p)).pages)
        except Exception as e:  # noqa: BLE001
            obs = f"No se pudo leer el PDF: {e}"
    return {"archivo": p.name, "ruta": str(p), "capa": "", "formato": p.suffix.lower().lstrip(".").upper(),
            "categoria": "documento", "n_registros": paginas, "campos": [], "fuente_procedencia": p.parent.name,
            "observacion": obs or "Documento complementario (soporte). Revisión manual."}


def copiar_originales(carpetas: list[Path], destino: Path):
    destino.mkdir(parents=True, exist_ok=True)
    for c in carpetas:
        shutil.copytree(c, destino / c.name, dirs_exist_ok=True)
