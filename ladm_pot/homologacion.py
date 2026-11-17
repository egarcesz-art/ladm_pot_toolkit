"""Fases 2-3 – Clasificación semántica, homologación de campos y dominios,
transformación geográfica y preparación de la estructura intermedia oficial.

Principios:
* Solo se asignan valores de dominio con coincidencia EXACTA normalizada
  (código ilicode, último segmento único o dispName oficial). Lo demás queda
  PENDIENTE con sugerencias; nunca se aproxima.
* No se asume sistema de coordenadas: si la capa no lo declara (y el formato no
  lo fija por especificación, como KML) la capa queda pendiente.
* Toda transformación se registra.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from pyproj import CRS, Transformer
from shapely.geometry import MultiPolygon, Polygon

from .modelo import Catalogo, Dominio, normalizar

log = logging.getLogger("ladm_pot")

FAMILIA = {"multipolygonz": "poligono", "linestringz": "linea", "pointz": "punto"}
GEOM_FAMILIA = {"Polygon": "poligono", "MultiPolygon": "poligono", "LineString": "linea",
                "MultiLineString": "linea", "Point": "punto", "MultiPoint": "punto"}


def es_texto(serie: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(serie) or pd.api.types.is_string_dtype(serie)


def buscar_campo(nombres: list[str], campos_norm: dict, usados=()) -> tuple[str | None, str]:
    """Busca un campo de origen por nombre normalizado exacto o, si no existe, por nombre
    truncado (límite de 10 caracteres del DBF/Shapefile) cuando la coincidencia es única."""
    for n in nombres:
        k = normalizar(n)
        if k in campos_norm and campos_norm[k] not in usados:
            return campos_norm[k], "exacto"
    for n in nombres:
        k = normalizar(n)
        cands = [orig for kn, orig in campos_norm.items()
                 if orig not in usados and 6 <= len(kn) <= 10 and len(kn) < len(k) and k.startswith(kn)]
        if len(cands) == 1:
            return cands[0], "truncado"
    return None, ""


def clave_capa(c: dict) -> str:
    return f"{c['archivo']}::{c.get('capa') or ''}"


# --------------------------------------------------------------------------
# Homologación de valores de dominio
# --------------------------------------------------------------------------

class IndiceDominio:
    def __init__(self, d: Dominio):
        self.dominio = d
        self.hojas = d.hojas()
        self.exacto: dict[str, set] = {}
        for cod, disp in self.hojas:
            claves = {normalizar(cod), normalizar(cod.split(".")[-1]), normalizar(disp),
                      normalizar(re.sub(r"^\(.*?\)\s*", "", disp or ""))}
            for k in claves:
                if k:
                    self.exacto.setdefault(k, set()).add(cod)
        self.no_hojas = {normalizar(n): n for n in d.nodos_intermedios()}

    def homologar(self, valor) -> tuple[str | None, str, list[str]]:
        """-> (codigo | None, metodo, sugerencias)"""
        if valor is None or (isinstance(valor, float) and np.isnan(valor)) or str(valor).strip() == "":
            return None, "vacio", []
        k = normalizar(valor)
        cands = self.exacto.get(k, set())
        if len(cands) == 1:
            return next(iter(cands)), "exacto_normalizado", []
        if len(cands) > 1:
            return None, "ambiguo", sorted(cands)
        if k in self.no_hojas:
            hijos = [c for c, _ in self.hojas if c.startswith(self.no_hojas[k] + ".")]
            return None, "valor_no_hoja", hijos
        toks = set(k.split("_"))
        sug = []
        for cod, disp in self.hojas:
            t2 = set(normalizar(cod).split("_")) | set(normalizar(disp).split("_"))
            if toks and toks <= t2:
                sug.append(cod)
        return None, "sin_correspondencia", sug[:6]

    def razon_coincidencia(self, serie: pd.Series, con_tokens=False) -> float:
        vals = serie.dropna().astype(str).str.strip()
        vals = vals[vals != ""].unique()
        if len(vals) == 0:
            return 0.0
        ok = 0
        for v in vals:
            cod, metodo, sug = self.homologar(v)
            if cod or (con_tokens and len(sug) == 1):
                ok += 1
        return ok / len(vals)


# --------------------------------------------------------------------------
# Clasificación de capas
# --------------------------------------------------------------------------

@dataclass
class ResultadoClasificacion:
    destino: str | None
    confianza: str
    puntaje: float
    alternativas: list = field(default_factory=list)
    motivo: str = ""


def clasificar_capa(capa: dict, gdf: gpd.GeoDataFrame | None, cat: Catalogo, reglas: dict,
                    indices: dict) -> ResultadoClasificacion:
    if capa.get("categoria") != "vector" or gdf is None or len(gdf) == 0:
        return ResultadoClasificacion(None, "NO_APLICA", 0, motivo="No es capa vectorial con registros")
    nombre = normalizar(f"{capa['archivo'].rsplit('.', 1)[0]}_{capa.get('capa') or ''}")
    tipos = set(gdf.geometry.dropna().geom_type)
    familias = {GEOM_FAMILIA.get(t) for t in tipos} - {None}
    campos_norm = {normalizar(c): c for c in gdf.columns if c != "geometry"}
    tablas = cat.intermedia["tablas"]
    puntajes = []
    for destino, regla in reglas["destinos"].items():
        if destino.startswith("_") and destino != "_limite_municipal":
            continue
        if not destino.startswith("_") and destino not in tablas:
            continue
        if regla.get("geometria") and familias and regla["geometria"] not in familias:
            continue
        # nombre
        hits = [k for k in regla["palabras_clave"] if normalizar(k) and normalizar(k) in nombre]
        s_nombre = min(1.0, 0.6 * len(hits) + (0.2 if any(len(normalizar(h)) > 8 for h in hits) else 0))
        # valores de dominio
        s_val = 0.0
        cols_dom = [col for (t, col), _ in cat.dominios_por_columna().items() if t == destino and not col.startswith("fuente_")]
        for col in cols_dom:
            idx = indices[(destino, col)]
            for c in campos_norm.values():
                if es_texto(gdf[c]):
                    s_val = max(s_val, idx.razon_coincidencia(gdf[c], con_tokens=True))
        # campos
        s_campos = 0.0
        if destino in tablas:
            objetivo = [c["nombre"] for c in tablas[destino] if not c["nombre"].startswith("fuente_") and c["geometria"] is None
                        and c["nombre"] not in ("identificador", "area_m2", "nombre")]
            if objetivo:
                encontrados = sum(1 for o in objetivo if buscar_campo([o] + reglas["sinonimos_campos"].get(o, []), campos_norm)[0])
                s_campos = encontrados / len(objetivo)
        sin_atributos = destino not in tablas  # destinos auxiliares (p. ej. límite municipal): solo nombre
        total = 0.75 * s_nombre if sin_atributos else 0.45 * s_nombre + 0.35 * s_val + 0.20 * s_campos
        puntajes.append((round(total, 3), destino, f"nombre={s_nombre:.2f} valores={s_val:.2f} campos={s_campos:.2f}"))
    puntajes.sort(reverse=True)
    if not puntajes or puntajes[0][0] < reglas["umbral_confianza_media"] * 0.5:
        return ResultadoClasificacion(None, "SIN_CORRESPONDENCIA", puntajes[0][0] if puntajes else 0,
                                      [p[1] for p in puntajes[:3]], "Ninguna tabla del modelo supera el umbral")
    mejor, segundo = puntajes[0], (puntajes[1] if len(puntajes) > 1 else (0, None, ""))
    margen = mejor[0] - segundo[0]
    if mejor[0] >= reglas["umbral_confianza_alta"] and margen >= 0.1:
        conf = "ALTA"
    elif mejor[0] >= reglas["umbral_confianza_media"]:
        conf = "MEDIA"
    else:
        conf = "BAJA"
    return ResultadoClasificacion(mejor[1], conf, mejor[0], [f"{p[1]} ({p[0]})" for p in puntajes[1:4]], mejor[2])


# --------------------------------------------------------------------------
# Sistema de referencia y geometría
# --------------------------------------------------------------------------

def resolver_crs(capa: dict, gdf: gpd.GeoDataFrame, decision: dict) -> tuple[CRS | None, str]:
    if decision.get("crs_origen"):
        return CRS.from_user_input(decision["crs_origen"]), f"Asignado por decisión del usuario ({decision['crs_origen']})"
    if gdf.crs is not None:
        return gdf.crs, "Declarado en el archivo (.prj / metadatos del formato)"
    if capa.get("formato") == "KML":
        return CRS.from_epsg(4326), "KML: WGS84 por especificación OGC KML"
    return None, "NO DECLARADO – requiere confirmación del usuario"


def preparar_geometrias(gdf: gpd.GeoDataFrame, familia: str, srid: int, registro: list, clave: str) -> gpd.GeoDataFrame:
    """Copia de trabajo: reproyecta, corrige validez, filtra familia, fuerza Z=0, explota si el destino es simple."""
    g = gdf.copy()
    g["_fid_origen"] = np.arange(len(g))
    n0 = len(g)
    vacias = g.geometry.isna() | g.geometry.is_empty
    if vacias.any():
        registro.append({"capa": clave, "operacion": "geometrías vacías excluidas", "n": int(vacias.sum()),
                         "detalle": f"fids origen: {list(g.loc[vacias, '_fid_origen'][:50])}"})
        g = g[~vacias]
    if g.crs is not None and g.crs.to_epsg() != srid:
        tr = Transformer.from_crs(g.crs, CRS.from_epsg(srid), always_xy=True)
        registro.append({"capa": clave, "operacion": f"reproyección {g.crs.to_string()} -> EPSG:{srid}", "n": len(g),
                         "detalle": tr.description})
        g = g.to_crs(epsg=srid)
    invalidas = ~g.geometry.is_valid
    if invalidas.any():
        razones = shapely.is_valid_reason(g.geometry[invalidas].values)
        registro.append({"capa": clave, "operacion": "corrección de geometrías inválidas (make_valid, copia de trabajo)",
                         "n": int(invalidas.sum()), "detalle": "; ".join(sorted(set(r.split("[")[0] for r in razones)))[:500]})
        g.loc[invalidas, "geometry"] = shapely.make_valid(g.geometry[invalidas].values)
    # filtrar a la familia destino (p. ej. polígonos dentro de GeometryCollection)
    def a_familia(geom):
        if geom is None:
            return None
        if familia == "poligono":
            partes = [p for p in getattr(geom, "geoms", [geom]) if p.geom_type in ("Polygon", "MultiPolygon")]
            polys = []
            for p in partes:
                polys += list(p.geoms) if p.geom_type == "MultiPolygon" else [p]
            return MultiPolygon(polys) if polys else None
        if familia == "linea":
            partes = [p for p in getattr(geom, "geoms", [geom]) if p.geom_type in ("LineString", "MultiLineString")]
            return shapely.union_all(partes) if partes else None
        partes = [p for p in getattr(geom, "geoms", [geom]) if p.geom_type in ("Point", "MultiPoint")]
        return shapely.union_all(partes) if partes else None
    g["geometry"] = [a_familia(x) for x in g.geometry]
    perdidas = g.geometry.isna() | g.geometry.is_empty
    if perdidas.any():
        registro.append({"capa": clave, "operacion": f"registros sin geometría de tipo {familia} tras la corrección (excluidos)",
                         "n": int(perdidas.sum()), "detalle": f"fids origen: {list(g.loc[perdidas, '_fid_origen'][:50])}"})
        g = g[~perdidas]
    if familia in ("linea", "punto"):
        antes = len(g)
        g = g.explode(index_parts=False)
        if len(g) != antes:
            registro.append({"capa": clave, "operacion": "multipartes separadas (el destino exige geometría simple)",
                             "n": len(g) - antes, "detalle": "Cada parte conserva el fid de origen"})
    if not g.empty and not g.geometry.has_z.all():
        registro.append({"capa": clave, "operacion": "coordenada Z=0 agregada (la estructura intermedia exige geometría Z)",
                         "n": int((~g.geometry.has_z).sum()), "detalle": "shapely.force_3d(z=0)"})
    g["geometry"] = shapely.force_3d(g.geometry.values, 0.0)
    g = g.set_crs(epsg=srid, allow_override=True)
    log.info("%s: %s -> %s registros preparados", clave, n0, len(g))
    return g


# --------------------------------------------------------------------------
# Homologación de una capa a una tabla de la estructura intermedia
# --------------------------------------------------------------------------

def mapear_campos(gdf: gpd.GeoDataFrame, destino: str, cat: Catalogo, reglas: dict, indices: dict,
                  decision_campos: dict) -> list[dict]:
    columnas = cat.intermedia["tablas"][destino]
    campos_norm = {normalizar(c): c for c in gdf.columns if c not in ("geometry", "_fid_origen")}
    usados, mapeo = set(), []
    for col in columnas:
        n = col["nombre"]
        if col["geometria"] or n.startswith("fuente_") or n == "area_m2":
            continue
        origen, metodo = None, ""
        if n in decision_campos:
            origen, metodo = decision_campos[n], "decisión del usuario"
            if origen not in gdf.columns:
                origen, metodo = None, f"decisión inválida: el campo '{decision_campos[n]}' no existe"
        elif buscar_campo([n], campos_norm, usados)[0]:
            origen, tipo = buscar_campo([n], campos_norm, usados)
            metodo = "nombre idéntico" if tipo == "exacto" else "nombre idéntico truncado (límite DBF de 10 caracteres)"
        else:
            sin = reglas["sinonimos_campos"].get(n, [])
            c0, tipo = buscar_campo(sin, campos_norm, usados)
            cand = [c0] if c0 else []
            etiqueta = "sinónimo de nombre de campo" + (" (nombre truncado DBF)" if tipo == "truncado" else "")
            if (destino, n) in indices:  # columna de dominio: elegir el campo con más valores homologables
                todos = [c for c in campos_norm.values() if c not in usados and es_texto(gdf[c])]
                ranking = sorted(((indices[(destino, n)].razon_coincidencia(gdf[c], True), c) for c in todos), reverse=True)
                if ranking and ranking[0][0] >= 0.5:
                    origen, metodo = ranking[0][1], f"valores coinciden con el dominio ({ranking[0][0]:.0%})"
                elif cand:
                    origen, metodo = cand[0], etiqueta
            elif cand:
                origen, metodo = cand[0], etiqueta
        if origen:
            usados.add(origen)
        mapeo.append({"columna_destino": n, "campo_origen": origen, "metodo": metodo or "sin correspondencia",
                      "obligatorio": col["obligatorio"], "dominio": indices[(destino, n)].dominio.nombre if (destino, n) in indices else ""})
    return mapeo


def homologar_capa(capa: dict, g: gpd.GeoDataFrame, destino: str, cat: Catalogo, reglas: dict, indices: dict,
                   proyecto: dict, decisiones: dict, registro_valores: list) -> tuple[gpd.GeoDataFrame, list[dict]]:
    clave = clave_capa(capa)
    dec_campos = decisiones.get("campos", {}).get(clave, {})
    dec_const = decisiones.get("constantes", {}).get(clave, {})
    dec_valores = decisiones.get("valores", {})
    mapeo = mapear_campos(g, destino, cat, reglas, indices, dec_campos)
    out = pd.DataFrame(index=g.index)
    columnas = cat.intermedia["tablas"][destino]
    for m in mapeo:
        n = m["columna_destino"]
        if n in dec_const:
            out[n] = dec_const[n]
            m["metodo"], m["campo_origen"] = "constante (decisión del usuario)", f"= {dec_const[n]}"
        elif m["campo_origen"]:
            out[n] = g[m["campo_origen"]]
        else:
            out[n] = None
    # fuentes: metadatos del proyecto (+ constantes por capa)
    for col in columnas:
        n = col["nombre"]
        if n.startswith("fuente_"):
            bloque = "fuente_administrativa" if n.startswith("fuente_administrativa") else "fuente_espacial"
            valor = dec_const.get(n, proyecto.get(bloque, {}).get(n))
            if n == "fuente_espacial_nombre" and not valor:
                valor = capa["archivo"] + (f" / {capa['capa']}" if capa.get("capa") else "")
            out[n] = valor
    # dominios
    for (t, n), idx in indices.items():
        if t != destino or n not in out.columns:
            continue
        clave_val = f"{destino}.{n}"
        mapa_usuario = {normalizar(k): v for k, v in dec_valores.get(clave_val, {}).items()}
        nuevos = []
        for v in out[n]:
            if v is None or (isinstance(v, float) and np.isnan(v)):
                nuevos.append(None)
                continue
            if normalizar(v) in mapa_usuario:
                cod = mapa_usuario[normalizar(v)]
                valido = cod in {c for c, _ in idx.hojas}
                nuevos.append(cod if valido else None)
                registro_valores.append({"capa": clave, "tabla": destino, "columna": n, "valor_origen": v,
                                         "valor_homologado": cod if valido else None,
                                         "metodo": "decisión del usuario" if valido else "DECISIÓN INVÁLIDA (código no existe en el dominio)",
                                         "sugerencias": ""})
                continue
            cod, metodo, sug = idx.homologar(v)
            if not cod and reglas.get("aplicar_coincidencia_por_tokens") and len(sug) == 1:
                cod, metodo = sug[0], "coincidencia única por tokens (habilitada en reglas)"
            nuevos.append(cod)
            registro_valores.append({"capa": clave, "tabla": destino, "columna": n, "valor_origen": v,
                                     "valor_homologado": cod, "metodo": metodo, "sugerencias": ", ".join(sug)})
        out[n] = nuevos
    # longitudes de texto
    for col in columnas:
        if col["longitud"] and col["nombre"] in out.columns:
            s = out[col["nombre"]]
            largo = s.dropna().astype(str).str.len()
            if (largo > col["longitud"]).any():
                registro_valores.append({"capa": clave, "tabla": destino, "columna": col["nombre"], "valor_origen": f"{int((largo > col['longitud']).sum())} valores",
                                         "valor_homologado": None, "metodo": f"EXCEDE longitud {col['longitud']} (no se trunca)", "sugerencias": ""})
    out["area_m2"] = g.geometry.area.round(1) if destino not in ("sistemas_generales_linea", "sistemas_generales_punto") else None
    res = gpd.GeoDataFrame(out, geometry=g.geometry.values, crs=g.crs)
    res["_fid_origen"] = g["_fid_origen"].values
    res["_capa_origen"] = clave
    return res, mapeo


def agregar_registros_valores(registro: list) -> pd.DataFrame:
    if not registro:
        return pd.DataFrame(columns=["capa", "tabla", "columna", "valor_origen", "valor_homologado", "metodo", "sugerencias", "n_registros"])
    df = pd.DataFrame(registro)
    df["valor_origen"] = df["valor_origen"].astype(str)
    return (df.groupby(["capa", "tabla", "columna", "valor_origen", "metodo", "sugerencias"], dropna=False)
              .agg(valor_homologado=("valor_homologado", "first"), n_registros=("valor_origen", "size")).reset_index())
