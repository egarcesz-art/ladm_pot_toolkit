"""Fase de validación.

Cada regla devuelve un estado: CUMPLE, CON_ADVERTENCIAS, FALLA, NO_EJECUTADA o SIN_DATOS.
El campo `origen` indica de dónde sale la regla:
  * "Oficial script 1/2"  -> estructura intermedia y dominios (SQL oficial del repositorio del modelo)
  * "Oficial T#/CL#/TM#"  -> validadores oficiales (VALIDADORES/*.md) reimplementados en Python
  * "Modelo ILI"           -> cardinalidades/asociaciones del archivo .ili
  * "Toolkit"              -> control de calidad adicional (no es requisito oficial)
"""
from __future__ import annotations

import datetime as dt
import logging
import shutil
import subprocess
from dataclasses import dataclass, field

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.strtree import STRtree

from .modelo import Catalogo

log = logging.getLogger("ladm_pot")
TOL_AREA = 1.0     # m²: superposiciones / vacíos menores se ignoran
TOL_LONG = 0.5     # m


@dataclass
class Resultado:
    id: str
    componente: str          # Estructural, Semántica, Espacial, Relacional, Documental, INTERLIS
    origen: str
    descripcion: str
    tabla: str = ""
    estado: str = "CUMPLE"
    severidad: str = ""
    n_evaluados: int = 0
    n_errores: int = 0
    detalles: list = field(default_factory=list)   # dicts: identificador, campo, problema, valor


def _vacio(g) -> bool:
    return g is None or len(g) == 0


def _fallo(r: Resultado, sev: str, detalles: list, advertencia=False):
    r.n_errores = len(detalles)
    r.detalles = detalles
    if detalles:
        r.estado = "CON_ADVERTENCIAS" if advertencia else "FALLA"
        r.severidad = sev
    return r


def _ids(g, mask) -> list:
    return list(g.loc[mask, "identificador"].astype(str)) if "identificador" in g.columns else list(g.index[mask])


def _superposiciones(g: gpd.GeoDataFrame, tol=TOL_AREA) -> list[dict]:
    geoms = g.geometry.values
    arbol = STRtree(geoms)
    a, b = arbol.query(geoms, predicate="intersects")
    out = []
    for i, j in zip(a, b):
        if i < j:
            inter = shapely.intersection(geoms[i], geoms[j])
            if inter.area > tol:
                out.append({"identificador": f"{g.iloc[i]['identificador']} / {g.iloc[j]['identificador']}",
                            "campo": "geometria", "problema": f"Superposición de {inter.area:,.1f} m²", "valor": ""})
    return out


def _lineas_superpuestas(g: gpd.GeoDataFrame) -> list[dict]:
    geoms = g.geometry.values
    arbol = STRtree(geoms)
    a, b = arbol.query(geoms, predicate="intersects")
    out = []
    for i, j in zip(a, b):
        if i < j:
            inter = shapely.intersection(geoms[i], geoms[j])
            if inter.length > TOL_LONG:
                out.append({"identificador": f"{g.iloc[i]['identificador']} / {g.iloc[j]['identificador']}",
                            "campo": "geometria", "problema": f"Líneas superpuestas/duplicadas en {inter.length:,.1f} m", "valor": ""})
    return out


def _cobertura(cubridora: gpd.GeoDataFrame, objetivo_geom, etiqueta: str) -> list[dict]:
    if objetivo_geom is None or objetivo_geom.is_empty:
        return []
    union = shapely.union_all(cubridora.geometry.values) if not _vacio(cubridora) else shapely.Polygon()
    falta = shapely.difference(objetivo_geom, union)
    partes = [p for p in getattr(falta, "geoms", [falta]) if p.area > TOL_AREA]
    return [{"identificador": f"vacío #{k + 1}", "campo": "geometria",
             "problema": f"{etiqueta}: {p.area:,.1f} m² sin cubrir", "valor": f"centroide {p.centroid.x:.1f}, {p.centroid.y:.1f}"}
            for k, p in enumerate(partes)]


def _fecha(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    try:
        return pd.to_datetime(v).date()
    except Exception:  # noqa: BLE001
        return None


def validar(tablas: dict[str, gpd.GeoDataFrame], municipio: pd.DataFrame, cat: Catalogo, indices: dict,
            limite: gpd.GeoDataFrame | None, config_interlis: dict | None = None) -> list[Resultado]:
    R: list[Resultado] = []
    srid = cat.srid
    esquema = cat.intermedia["tablas"]

    # ------------------------------------------------------------------ ESTRUCTURAL
    for t, cols in esquema.items():
        g = municipio if t == "municipio" else tablas.get(t)
        r = Resultado(f"E1.{t}", "Estructural", "Oficial script 1", f"Tabla '{t}' con las {len(cols)} columnas oficiales", t)
        if g is None:
            r.estado, r.severidad = "SIN_DATOS", "MEDIO"
            r.detalles = [{"identificador": "", "campo": "", "valor": "",
                           "problema": "Tabla creada vacía en la estructura intermedia: no se cargó información para esta temática"}]
            R.append(r)
            continue
        faltan = [c["nombre"] for c in cols if c["nombre"] not in g.columns and not (c["geometria"] and "geometry" in g.columns)]
        r.n_evaluados = len(cols)
        R.append(_fallo(r, "CRÍTICO", [{"identificador": "", "campo": f, "problema": "Columna faltante", "valor": ""} for f in faltan]))
        if len(g) == 0:
            R.append(Resultado(f"E0.{t}", "Estructural", "Toolkit", f"Tabla '{t}' con registros", t, "SIN_DATOS", "MEDIO", 0, 0,
                               [{"identificador": "", "campo": "", "problema": "No se cargó información en esta tabla", "valor": ""}]))
            continue
        # NOT NULL
        r2 = Resultado(f"E2.{t}", "Estructural", "Oficial script 1 (NOT NULL)", f"Campos obligatorios diligenciados en '{t}'", t, n_evaluados=len(g))
        det = []
        for c in cols:
            if c["obligatorio"] and c["nombre"] in g.columns:
                s = g[c["nombre"]]
                nulos = s.isna() | (s.astype(str).str.strip().isin(["", "None", "nan"]))
                for i in _ids(g, nulos)[:200]:
                    det.append({"identificador": i, "campo": c["nombre"], "problema": "Campo obligatorio vacío", "valor": ""})
        R.append(_fallo(r2, "CRÍTICO", det))
        # longitudes
        r3 = Resultado(f"E3.{t}", "Estructural", "Oficial script 1 (varchar)", f"Longitud de textos en '{t}'", t, n_evaluados=len(g))
        det = []
        for c in cols:
            if c["longitud"] and c["nombre"] in g.columns:
                largo = g[c["nombre"]].dropna().astype(str).str.len()
                for i in largo[largo > c["longitud"]].index[:100]:
                    det.append({"identificador": g.loc[i, "identificador"] if "identificador" in g else i, "campo": c["nombre"],
                                "problema": f"Texto de {largo[i]} caracteres (máx. {c['longitud']})", "valor": ""})
        R.append(_fallo(r3, "ALTO", det))
        # geometría: tipo y SRID
        gcol = next((c for c in cols if c["geometria"]), None)
        if gcol and isinstance(g, gpd.GeoDataFrame):
            r4 = Resultado(f"E4.{t}", "Estructural", "Oficial script 1 (geometry)", f"Tipo {gcol['geometria']} y SRID {gcol['srid']} en '{t}'", t, n_evaluados=len(g))
            det = []
            if g.crs is None or g.crs.to_epsg() != gcol["srid"]:
                det.append({"identificador": "", "campo": "geometria", "problema": f"SRID {g.crs.to_epsg() if g.crs else 'ninguno'} ≠ {gcol['srid']}", "valor": ""})
            esperado = {"multipolygonz": "MultiPolygon", "linestringz": "LineString", "pointz": "Point"}[gcol["geometria"]]
            malos = (g.geom_type != esperado) | (~g.geometry.has_z)
            for i in _ids(g, malos)[:100]:
                det.append({"identificador": i, "campo": "geometria", "problema": f"Geometría distinta de {gcol['geometria']}", "valor": ""})
            R.append(_fallo(r4, "CRÍTICO", det))
        # identificador único
        if "identificador" not in g.columns:
            continue
        r5 = Resultado(f"E5.{t}", "Relacional", "Toolkit", f"Identificadores únicos en '{t}'", t, n_evaluados=len(g))
        dup = g["identificador"].duplicated(keep=False) & g["identificador"].notna()
        R.append(_fallo(r5, "ALTO", [{"identificador": i, "campo": "identificador", "problema": "Identificador repetido", "valor": ""} for i in _ids(g, dup)]))

    # ------------------------------------------------------------------ SEMÁNTICA (dominios script 2)
    for regla in cat.reglas_dominio:
        t, c = regla["tabla"], regla["columna"]
        g = municipio if t == "municipio" else tablas.get(t)
        if g is None or len(g) == 0 or c not in g.columns:
            continue
        idx = indices.get((t, c))
        r = Resultado(f"S1.{t}.{c}", "Semántica", "Oficial script 2", regla["mensaje_oficial"] or f"Dominio de {c}", t, n_evaluados=len(g))
        if idx is None:
            r.estado, r.detalles = "NO_EJECUTADA", [{"identificador": "", "campo": c, "problema": f"Dominio {regla['tabla_dominio']} no encontrado en el .ili", "valor": ""}]
            R.append(r)
            continue
        validos = {cod for cod, _ in idx.hojas}
        s = g[c]
        malos = s.notna() & ~s.astype(str).isin(validos)
        R.append(_fallo(r, "ALTO", [{"identificador": i, "campo": c, "problema": "Valor fuera del dominio", "valor": v}
                                    for i, v in zip(_ids(g, malos), s[malos])]))
    for t in ("areas_actividad", "tratamiento_urbanistico", "clasificacion_suelo", "zonificacion_suelo_rural", "suelo_proteccion_urbano",
              "centro_poblado_rural", "zonificacion_amenaza", "area_condicion_amenaza", "area_condicion_riesgo",
              "sistemas_generales_poligono", "sistemas_generales_linea", "sistemas_generales_punto"):
        g = tablas.get(t)
        if _vacio(g):
            continue
        r = Resultado(f"S2.{t}", "Semántica", "Oficial script 2 (DRR)", "Al menos una descripción de derecho, restricción o responsabilidad", t, n_evaluados=len(g))
        m = g[["descripcion_derecho", "descripcion_restriccion", "descripcion_responsabilidad"]].isna().all(axis=1)
        R.append(_fallo(r, "ALTO", [{"identificador": i, "campo": "descripcion_*", "problema": "Sin derecho, restricción ni responsabilidad", "valor": ""} for i in _ids(g, m)]))

    # Validadores oficiales de consistencia lógica y temáticos (selección implementable sobre la estructura intermedia)
    def regla_simple(cod, tabla, desc, mascara_fn, campo, sev="ALTO"):
        g = tablas.get(tabla)
        if _vacio(g):
            return
        r = Resultado(cod, "Semántica", f"Oficial {cod.split('.')[0]}", desc, tabla, n_evaluados=len(g))
        m = mascara_fn(g)
        R.append(_fallo(r, sev, [{"identificador": i, "campo": campo, "problema": desc, "valor": ""} for i in _ids(g, m)]))

    regla_simple("CL2", "centro_poblado_rural", "Centro poblado sin código DANE/municipal", lambda g: g["codigo"].isna(), "codigo")
    regla_simple("CL16", "zonificacion_suelo_rural", "Zonificación rural sin tipo de categoría (fuente posterior al 20-09-2007)",
                 lambda g: g["tipo_categoria_rural"].isna() & g["fuente_administrativa_fecha_documento"].map(lambda v: (_fecha(v) or dt.date(1900, 1, 1)) > dt.date(2007, 9, 20)),
                 "tipo_categoria_rural")
    regla_simple("CL29", "area_condicion_amenaza", "Área en condición de amenaza sin categoría (instrumento posterior al 19-09-2014)",
                 lambda g: g["categoria_amenaza"].isna() & g["fuente_administrativa_fecha_documento"].map(lambda v: (_fecha(v) or dt.date(1900, 1, 1)) > dt.date(2014, 9, 19)),
                 "categoria_amenaza")
    regla_simple("CL30", "area_condicion_riesgo", "Área en condición de riesgo sin priorización", lambda g: g["priorizacion"].isna(), "priorizacion")
    regla_simple("TM2", "zonificacion_amenaza", "Zonificación de amenaza sin categoría", lambda g: g["categoria_amenaza"].isna(), "categoria_amenaza")
    regla_simple("TM3", "zonificacion_suelo_rural",
                 "Categoría de conservación y protección ambiental con uso principal distinto de Conservacion_Proteccion_Ambiental.*",
                 lambda g: g["tipo_categoria_rural"].fillna("").str.startswith("Proteccion_Suelo_Rural.Conservacion_Proteccion_Ambiental")
                 & ~g["uso_principal"].fillna("").str.startswith("Conservacion_Proteccion_Ambiental"), "uso_principal")
    regla_simple("TM4", "zonificacion_suelo_rural", "Uso principal Centro_Poblado fuera de la categoría Desarrollo_Restringido.Centro_Poblado_Rural",
                 lambda g: (g["uso_principal"] == "Centro_Poblado") & (g["tipo_categoria_rural"] != "Desarrollo_Restringido.Centro_Poblado_Rural"), "uso_principal")
    if not _vacio(municipio):
        m = municipio
        r = Resultado("CL1/CL6-8", "Semántica", "Oficial CL1, CL6, CL7, CL8", "Interesado municipio: NIT, códigos DIVIPOLA (2 y 3 dígitos) y nombre", "municipio", n_evaluados=len(m))
        det = []
        for _, f in m.iterrows():
            if f.get("tipo_documento") != "NIT":
                det.append({"identificador": "municipio", "campo": "tipo_documento", "problema": "Debe ser NIT (CL1)", "valor": f.get("tipo_documento")})
            if not str(f.get("codigo_departamento") or "").isdigit() or len(str(f.get("codigo_departamento"))) != 2:
                det.append({"identificador": "municipio", "campo": "codigo_departamento", "problema": "Código de departamento DIVIPOLA de 2 dígitos (CL6)", "valor": f.get("codigo_departamento")})
            if not str(f.get("codigo_municipio") or "").isdigit() or len(str(f.get("codigo_municipio"))) != 3:
                det.append({"identificador": "municipio", "campo": "codigo_municipio", "problema": "Código de municipio DIVIPOLA de 3 dígitos (CL7)", "valor": f.get("codigo_municipio")})
            if not f.get("nombre_municipio"):
                det.append({"identificador": "municipio", "campo": "nombre_municipio", "problema": "Nombre del municipio vacío (CL8)", "valor": ""})
            if not f.get("numero_documento"):
                det.append({"identificador": "municipio", "campo": "numero_documento", "problema": "NIT del municipio sin diligenciar", "valor": ""})
        R.append(_fallo(r, "ALTO", det))
        R[-1].detalles.append({"identificador": "", "campo": "", "problema": "Nota: la existencia del código en DIVIPOLA no se puede verificar sin la tabla oficial del DANE", "valor": ""})

    # ------------------------------------------------------------------ ESPACIAL
    for t, g in tablas.items():
        if _vacio(g):
            continue
        r = Resultado(f"G1.{t}", "Espacial", "Toolkit", "Geometrías válidas (OGC) y no vacías", t, n_evaluados=len(g))
        m = ~g.geometry.is_valid | g.geometry.is_empty
        R.append(_fallo(r, "ALTO", [{"identificador": i, "campo": "geometria", "problema": "Geometría inválida o vacía", "valor": ""} for i in _ids(g, m)]))
        if g.geom_type.iloc[0] == "MultiPolygon":
            r = Resultado(f"CL3.{t}", "Espacial", "Oficial CL3", "Área distinta de cero", t, n_evaluados=len(g))
            R.append(_fallo(r, "ALTO", [{"identificador": i, "campo": "geometria", "problema": "Área = 0", "valor": ""} for i in _ids(g, g.area <= 0)]))
        elif g.geom_type.iloc[0] == "LineString":
            r = Resultado(f"CL4.{t}", "Espacial", "Oficial CL4", "Longitud distinta de cero", t, n_evaluados=len(g))
            R.append(_fallo(r, "ALTO", [{"identificador": i, "campo": "geometria", "problema": "Longitud = 0", "valor": ""} for i in _ids(g, g.length <= 0)]))
        r = Resultado(f"G2.{t}", "Espacial", "Toolkit", "Geometrías duplicadas exactas", t, n_evaluados=len(g))
        d = g.geometry.to_wkb().duplicated(keep=False)
        R.append(_fallo(r, "MEDIO", [{"identificador": i, "campo": "geometria", "problema": "Geometría duplicada", "valor": ""} for i in _ids(g, d)], advertencia=True))
        if limite is not None and not limite.empty:
            lim = shapely.union_all(limite.geometry.values).buffer(1.0)
            r = Resultado(f"G3.{t}", "Espacial", "Toolkit", "Objetos dentro del límite municipal (tolerancia 1 m)", t, n_evaluados=len(g))
            fuera = ~g.geometry.within(lim)
            R.append(_fallo(r, "MEDIO", [{"identificador": i, "campo": "geometria", "problema": "Sale del límite municipal", "valor": ""} for i in _ids(g, fuera)], advertencia=True))

    for cod, t, desc in (("T1", "clasificacion_suelo", "Sin superposición en clasificación del suelo"),
                         ("T5", "zonificacion_suelo_rural", "Sin superposición en zonificación del suelo rural"),
                         ("T6", "tratamiento_urbanistico", "Sin superposición en tratamientos urbanísticos"),
                         ("T8", "areas_actividad", "Sin superposición en áreas de actividad")):
        g = tablas.get(t)
        if _vacio(g):
            continue
        r = Resultado(cod, "Espacial", f"Oficial {cod}", desc, t, n_evaluados=len(g))
        R.append(_fallo(r, "ALTO", _superposiciones(g)))

    cs = tablas.get("clasificacion_suelo")
    def clase(valores):
        if _vacio(cs):
            return None
        sel = cs[cs["tipo_clasificacion_suelo"].isin(valores)]
        return shapely.union_all(sel.geometry.values) if len(sel) else None
    urbano, urb_exp, rural = clase(["Urbano"]), clase(["Urbano", "Expansion_Urbana"]), clase(["Rural"])

    if not _vacio(tablas.get("areas_actividad")) and urbano is not None:
        r = Resultado("T10", "Espacial", "Oficial T10", "Áreas de actividad cubren todo el suelo urbano", "areas_actividad", n_evaluados=1)
        R.append(_fallo(r, "ALTO", _cobertura(tablas["areas_actividad"], urbano, "Suelo urbano")))
    if not _vacio(tablas.get("tratamiento_urbanistico")) and urb_exp is not None:
        r = Resultado("T12", "Espacial", "Oficial T12", "Tratamientos cubren suelo urbano y de expansión", "tratamiento_urbanistico", n_evaluados=1)
        R.append(_fallo(r, "ALTO", _cobertura(tablas["tratamiento_urbanistico"], urb_exp, "Suelo urbano/expansión")))
    sl = tablas.get("sistemas_generales_linea")
    if not _vacio(sl):
        vias = sl[sl["tipo_sistema_general"].fillna("").str.startswith("Vias")]
        if len(vias):
            r = Resultado("T13", "Espacial", "Oficial T13", "Vías (líneas) sin duplicados ni superposiciones", "sistemas_generales_linea", n_evaluados=len(vias))
            R.append(_fallo(r, "ALTO", _lineas_superpuestas(vias.reset_index(drop=True))))
    sp = tablas.get("sistemas_generales_punto")
    if not _vacio(sp):
        pts = sp[sp["tipo_sistema_general"].fillna("").str.match(r"^(Equipamientos|Servicios_Publicos|Infraestructura_Transporte)")]
        r = Resultado("T15", "Espacial", "Oficial T15", "Puntos de sistemas generales sin superposición", "sistemas_generales_punto", n_evaluados=len(pts))
        d = pts.geometry.to_wkb().duplicated(keep=False)
        R.append(_fallo(r, "ALTO", [{"identificador": i, "campo": "geometria", "problema": "Punto superpuesto", "valor": ""} for i in _ids(pts, d)]))
    if not _vacio(cs):
        todo = shapely.union_all(cs.geometry.values).buffer(0.5)
        for t in ("sistemas_generales_linea", "sistemas_generales_punto", "sistemas_generales_poligono"):
            g = tablas.get(t)
            if _vacio(g):
                continue
            sel = g[g["tipo_sistema_general"].fillna("").str.match(r"^(Vias|Servicios_Publicos|Infraestructura_Transporte)")]
            if not len(sel):
                continue
            r = Resultado(f"T16.{t}", "Espacial", "Oficial T16", "Sistemas generales (vías, servicios, transporte) dentro de la clasificación del suelo", t, n_evaluados=len(sel))
            fuera = ~sel.geometry.within(todo)
            R.append(_fallo(r, "MEDIO", [{"identificador": i, "campo": "geometria", "problema": "Por fuera de la clasificación del suelo", "valor": ""} for i in _ids(sel, fuera)], advertencia=True))
    cp = tablas.get("centro_poblado_rural")
    if not _vacio(cp):
        r = Resultado("T17/TM1", "Relacional", "Oficial T17, TM1 + asociación pot_clasificacionsuelo_centropoblado {1}",
                      "Centros poblados contenidos en suelo Rural", "centro_poblado_rural", n_evaluados=len(cp))
        if rural is None:
            r.estado, r.detalles = "NO_EJECUTADA", [{"identificador": "", "campo": "", "problema": "No hay suelo Rural en clasificacion_suelo", "valor": ""}]
            R.append(r)
        else:
            fuera = ~cp.geometry.within(rural.buffer(0.5))
            R.append(_fallo(r, "ALTO", [{"identificador": i, "campo": "geometria", "problema": "Centro poblado fuera del suelo rural", "valor": ""} for i in _ids(cp, fuera)]))
        zr = tablas.get("zonificacion_suelo_rural")
        r = Resultado("T18", "Relacional", "Oficial T18 + asociación pot_zonificacionsuelo_centropoblado {1}",
                      "Límite del centro poblado coincide con zonificación rural 'Desarrollo_Restringido.Centro_Poblado_Rural'", "centro_poblado_rural", n_evaluados=len(cp))
        if _vacio(zr):
            r.estado, r.detalles = "NO_EJECUTADA", [{"identificador": "", "campo": "", "problema": "Sin zonificación rural", "valor": ""}]
            R.append(r)
        else:
            zcp = zr[zr["tipo_categoria_rural"] == "Desarrollo_Restringido.Centro_Poblado_Rural"]
            det = []
            for i, f in cp.iterrows():
                cand = zcp[zcp.intersects(f.geometry)]
                ok = any(shapely.symmetric_difference(f.geometry, z).area <= TOL_AREA for z in cand.geometry)
                if not ok:
                    det.append({"identificador": f["identificador"], "campo": "geometria", "problema": "Sin polígono coincidente en la zonificación rural de centro poblado", "valor": ""})
            R.append(_fallo(r, "ALTO", det))
    zr = tablas.get("zonificacion_suelo_rural")
    if not _vacio(zr):
        r = Resultado("R1", "Relacional", "Modelo ILI: pot_clasificacionsuelo_zonificacionsuelo {1}",
                      "Cada zona rural pertenece a la clase de suelo Rural", "zonificacion_suelo_rural", n_evaluados=len(zr))
        if rural is None:
            r.estado, r.detalles = "NO_EJECUTADA", [{"identificador": "", "campo": "", "problema": "No hay suelo Rural en clasificacion_suelo", "valor": ""}]
            R.append(r)
        else:
            fuera = ~zr.geometry.within(rural.buffer(0.5))
            R.append(_fallo(r, "ALTO", [{"identificador": i, "campo": "geometria", "problema": "Zona rural fuera del suelo Rural", "valor": ""} for i in _ids(zr, fuera)]))
    if not _vacio(zr) and rural is not None:
        r = Resultado("G5", "Espacial", "Toolkit (no es validador oficial)", "La zonificación rural cubre todo el suelo Rural",
                      "zonificacion_suelo_rural", n_evaluados=1)
        R.append(_fallo(r, "MEDIO", _cobertura(zr, rural, "Suelo rural sin zonificar"), advertencia=True))
    if not _vacio(cs) and limite is not None and not limite.empty:
        r = Resultado("G4", "Espacial", "Toolkit", "La clasificación del suelo cubre todo el municipio (sin vacíos)", "clasificacion_suelo", n_evaluados=1)
        R.append(_fallo(r, "ALTO", _cobertura(cs, shapely.union_all(limite.geometry.values), "Territorio municipal")))
    if (not _vacio(tablas.get("area_condicion_amenaza")) or not _vacio(tablas.get("area_condicion_riesgo"))) and _vacio(tablas.get("zonificacion_amenaza")):
        R.append(Resultado("CL27", "Relacional", "Oficial CL27", "Hay áreas en condición de amenaza/riesgo sin zonificación de amenazas",
                           "zonificacion_amenaza", "CON_ADVERTENCIAS", "ALTO", 1, 1,
                           [{"identificador": "", "campo": "", "problema": "Alerta oficial CL27: falta la zonificación de amenazas", "valor": ""}]))

    # ------------------------------------------------------------------ DOCUMENTAL
    for t, g in tablas.items():
        if _vacio(g):
            continue
        r = Resultado(f"D1.{t}", "Documental", "Modelo ILI (POT_FuenteEspacial / COL_Fuente) + Toolkit",
                      "Fuente espacial con tipo, escala, fecha, responsable y metadato", t, n_evaluados=len(g))
        det = []
        for c in ("fuente_espacial_tipo", "fuente_espacial_escala", "fuente_espacial_fecha_documento", "fuente_espacial_responsable", "fuente_espacial_metadato"):
            if g[c].isna().all():
                det.append({"identificador": "(toda la tabla)", "campo": c, "problema": "Sin diligenciar", "valor": ""})
        R.append(_fallo(r, "BAJO", det, advertencia=True))
        r = Resultado(f"D2.{t}", "Documental", "Modelo ILI (POT_FuenteAdministrativa)", "Fuente administrativa con número y fecha del acto", t, n_evaluados=len(g))
        det = [{"identificador": "(toda la tabla)", "campo": c, "problema": "Sin diligenciar", "valor": ""}
               for c in ("fuente_administrativa_numero_fuente", "fuente_administrativa_fecha_documento") if g[c].isna().all()]
        R.append(_fallo(r, "MEDIO", det, advertencia=True))

    # ------------------------------------------------------------------ INTERLIS
    R.append(validar_interlis(config_interlis or {}))
    return R


def validar_interlis(cfg: dict) -> Resultado:
    r = Resultado("I1", "INTERLIS", "ilivalidator sobre XTF", "Validación del archivo de transferencia XTF contra el modelo")
    xtf, jar = cfg.get("xtf"), cfg.get("ilivalidator_jar")
    if not (xtf and jar and shutil.which("java")):
        r.estado = "NO_EJECUTADA"
        r.detalles = [{"identificador": "", "campo": "", "valor": "",
                       "problema": "Requiere el XTF (generado tras cargar la estructura intermedia en PostGIS y ejecutar el ETL oficial) y ilivalidator.jar. Ver 04_BASE_DATOS_LADM_COL_POT/fase4_migracion."}]
        return r
    proc = subprocess.run(["java", "-jar", jar, "--modeldir", cfg["modeldir"], "--log", cfg["log"], xtf],
                          capture_output=True, text=True, timeout=3600)
    r.n_evaluados = 1
    if proc.returncode == 0:
        r.estado = "CUMPLE"
    else:
        r.estado, r.severidad = "FALLA", "CRÍTICO"
        r.detalles = [{"identificador": "", "campo": "", "problema": l, "valor": ""} for l in proc.stdout.splitlines()[-200:] if "Error" in l]
    return r


def resumen_cumplimiento(resultados: list[Resultado]) -> pd.DataFrame:
    filas = []
    for comp in ("Estructural", "Semántica", "Espacial", "Relacional", "Documental", "INTERLIS"):
        rs = [r for r in resultados if r.componente == comp]
        evaluadas = [r for r in rs if r.estado in ("CUMPLE", "FALLA", "CON_ADVERTENCIAS")]
        cumplen = [r for r in evaluadas if r.estado == "CUMPLE"]
        filas.append({"componente": comp, "reglas_totales": len(rs), "reglas_evaluadas": len(evaluadas),
                      "cumplen": len(cumplen), "con_advertencias": sum(r.estado == "CON_ADVERTENCIAS" for r in rs),
                      "fallan": sum(r.estado == "FALLA" for r in rs),
                      "no_ejecutadas": sum(r.estado == "NO_EJECUTADA" for r in rs), "sin_datos": sum(r.estado == "SIN_DATOS" for r in rs),
                      "porcentaje_cumplimiento_reglas_evaluadas": round(100 * len(cumplen) / len(evaluadas), 1) if evaluadas else None})
    return pd.DataFrame(filas)
