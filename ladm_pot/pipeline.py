"""Orquestador por lotes: insumos -> carpeta de entrega LADM_COL-POT."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
import shutil
import sys
import traceback
from collections import Counter
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

from . import homologacion as H
from . import inventario as I
from . import salida as S
from . import validacion as V
from .modelo import Catalogo, normalizar

log = logging.getLogger("ladm_pot")
BASE = Path(__file__).resolve().parent.parent
ABREV = {"clasificacion_suelo": "CS", "zonificacion_suelo_rural": "ZR", "areas_actividad": "AA", "tratamiento_urbanistico": "TU",
         "suelo_proteccion_urbano": "SP", "centro_poblado_rural": "CP", "zonificacion_amenaza": "ZA", "area_condicion_amenaza": "CA",
         "area_condicion_riesgo": "CR", "sistemas_generales_poligono": "SGA", "sistemas_generales_linea": "SGL", "sistemas_generales_punto": "SGP"}
COMPLEMENTARIAS = ("sistemas_generales_poligono", "sistemas_generales_linea", "sistemas_generales_punto",
                   "zonificacion_amenaza", "area_condicion_amenaza", "area_condicion_riesgo")

SOLUCIONES = {
    "Campo obligatorio vacío": "Diligenciar en la fuente o mapear el campo en decisiones.json (campos/constantes).",
    "Valor fuera del dominio": "Registrar la equivalencia en decisiones.json > valores usando el código oficial (ilicode).",
    "Superposición": "Depurar la topología en la capa de origen (copia de trabajo) y volver a ejecutar.",
    "sin cubrir": "Completar la cobertura en la capa de origen o revisar la clasificación del suelo.",
    "Sin derecho, restricción ni responsabilidad": "Diligenciar al menos una descripción (derecho/restricción/responsabilidad) desde el acuerdo.",
}


def _sol(problema: str) -> str:
    for k, v in SOLUCIONES.items():
        if k.lower() in problema.lower():
            return v
    return "Revisar y corregir en la fuente; documentar la decisión."


def configurar_log(path: Path):
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(sh)


def correspondencia_clases(cat: Catalogo) -> pd.DataFrame:
    sql = (cat.carpeta / "ESTRUCTURA_INTERMEDIA" / "4_etl_intermediate_structure_to_ladm_col_pot.sql").read_text(encoding="utf-8", errors="replace")
    filas = set()
    for bloque in re.split(r";\s*\n", sql):
        ins = re.search(r"insert into\s+(pot_\w+)", bloque, re.I)
        froms = {t for t in re.findall(r"(?:from|join)\s+(\w+)", bloque, re.I) if t in cat.intermedia["tablas"]}
        if ins:
            for f in froms:
                filas.add((f, ins.group(1).lower()))
    clases = {c.lower(): c for c in cat.clases}
    return pd.DataFrame([{"tabla_estructura_intermedia": a, "tabla_ili2db_destino": b, "clase_modelo": clases.get(b, "(tabla de estructura/asociación)")}
                         for a, b in sorted(filas)])


def detectar_municipio(capas, lectura) -> dict:
    """Busca códigos DIVIPOLA de 5 dígitos en campos típicos. Solo informa; no decide."""
    cont = Counter()
    for c in capas:
        g = lectura.get(c["id"])
        if g is None:
            continue
        for col in g.columns:
            if any(k in normalizar(col) for k in ("MPIO", "MUNICIPIO", "DANE", "DIVIPOLA", "COD_MUN")):
                for v in g[col].dropna().astype(str):
                    if re.fullmatch(r"\d{5}", v.strip()):
                        cont[v.strip()] += 1
    return {"candidatos_codigo_dane": cont.most_common(3)}


def ejecutar(insumos: list[Path], salida: Path, proyecto_path: Path | None, decisiones_path: Path | None,
             modelo_dir: Path, reglas_path: Path, prueba=False, interlis: dict | None = None) -> Path:
    t0 = dt.datetime.now()
    proyecto = json.loads(proyecto_path.read_text(encoding="utf-8")) if proyecto_path else {}
    decisiones = json.loads(decisiones_path.read_text(encoding="utf-8")) if decisiones_path and decisiones_path.exists() else {}
    reglas = json.loads(reglas_path.read_text(encoding="utf-8"))
    mun = proyecto.get("municipio", {})
    dane = f"{mun.get('codigo_departamento') or ''}{mun.get('codigo_municipio') or ''}" or "SINDANE"
    nombre_mun = normalizar(mun.get("nombre_municipio") or "SIN_MUNICIPIO")
    depto = normalizar(mun.get("departamento") or "SIN_DEPARTAMENTO")
    raiz = salida / f"LADM_COL_POT_{dane}_{nombre_mun}_{depto}"
    if raiz.exists():
        shutil.rmtree(raiz)
    rutas = S.crear_estructura(raiz)
    configurar_log(rutas["08"] / "bitacora_procesamiento.log")
    log.info("Inicio del procesamiento. Raíz: %s", raiz)
    obs: list[dict] = []          # observaciones del procesamiento
    transformaciones: list[dict] = []
    valores_log: list[dict] = []
    pendientes: list[str] = []

    def observar(sev, archivo, capa, campo, problema, regla, desc, solucion, estado="Pendiente"):
        obs.append({"severidad": sev, "archivo": archivo, "capa": capa, "campo_o_elemento": campo, "problema": problema,
                    "regla_relacionada": regla, "descripcion": desc, "solucion_sugerida": solucion, "estado_correccion": estado})

    # ---------------------------------------------------------------- 1. modelo
    cat = Catalogo(modelo_dir)
    log.info("Modelo leído: %s", cat.resumen()["modelos"])
    indices = {k: H.IndiceDominio(d) for k, d in cat.dominios_por_columna().items()}
    for m in cat.modelos:
        if m["modelo"] == "LADM_COL_v_2_0_0_Ext_POT" and m["version"] != "2.0.0":
            observar("ALTO", m["archivo"], "", "VERSION", f"Versión del modelo {m['version']}", "Resolución 0058 de 2025",
                     "La versión leída no es la 2.0.0 adoptada", "Confirmar la versión oficial aplicable")

    # ---------------------------------------------------------------- 2. insumos e inventario
    I.copiar_originales(insumos, rutas["01"])
    trabajo = rutas["03"] / "_trabajo"
    eventos_zip = I.extraer_comprimidos(rutas["01"], trabajo / "extraidos")
    capas, archivos = I.inventariar([rutas["01"], trabajo / "extraidos"] if (trabajo / "extraidos").exists() else [rutas["01"]])
    log.info("Inventario: %d archivos, %d capas/elementos", len(archivos), len(capas))
    for c in capas:
        if c["categoria"] == "error_lectura":
            observar("ALTO", c["archivo"], c.get("capa", ""), "", "Error de lectura", "Inventario", c.get("observacion", ""), "Revisar el archivo o convertirlo a GPKG/SHP")

    # ---------------------------------------------------------------- 3. clasificación
    lectura: dict[str, gpd.GeoDataFrame] = {}
    clasif = []
    for c in capas:
        if c["categoria"] != "vector":
            continue
        try:
            if c["formato"] == "CSV con coordenadas":
                df = pd.read_csv(c["ruta"], sep=None, engine="python")
                g, _ = I._csv_a_puntos(df)
            else:
                g = I.leer_vector(c["ruta"], c["capa"] or None)
            lectura[c["id"]] = g
        except Exception as e:  # noqa: BLE001
            observar("ALTO", c["archivo"], c["capa"], "", "No se pudo leer la capa", "Inventario", str(e), "Revisar el archivo")
            continue
        res = H.clasificar_capa(c, g, cat, reglas, indices)
        clave = H.clave_capa(c)
        dec = decisiones.get("capas", {}).get(clave, {})
        destino, estado = res.destino, ""
        if dec.get("destino"):
            destino, estado = (None, "EXCLUIDA por decisión") if dec["destino"] == "excluir" else (dec["destino"], "CONFIRMADA por decisión")
        elif res.confianza == "ALTA":
            estado = "AUTOMÁTICA (confianza alta)"
        elif res.confianza in ("MEDIA", "BAJA"):
            estado = "PENDIENTE (confirmar destino)"
        else:
            estado = "SIN CORRESPONDENCIA (se conserva, no se descarta)"
        clasif.append({"id": c["id"], "clave": clave, "archivo": c["archivo"], "capa": c["capa"], "destino_sugerido": res.destino,
                       "confianza": res.confianza, "puntaje": res.puntaje, "motivo": res.motivo, "alternativas": "; ".join(res.alternativas),
                       "destino_final": destino if estado.startswith(("AUTOM", "CONFIRM")) else None, "estado": estado})
        if estado.startswith("PENDIENTE"):
            pendientes.append(f"{clave}: confirmar destino (sugerido '{res.destino}', confianza {res.confianza})")
            observar("MEDIO", c["archivo"], c["capa"], "capa", "Clasificación no confirmada", "Motor de clasificación",
                     f"Sugerido: {res.destino} ({res.motivo})", "Confirmar en decisiones.json > capas")
    cl = pd.DataFrame(clasif)  # se reconstruye al final con estados actualizados

    # ---------------------------------------------------------------- 4. CRS + geometría (copias de trabajo)
    preparadas: dict[str, gpd.GeoDataFrame] = {}
    crs_doc = []
    for f in clasif:
        if not f["destino_final"]:
            continue
        c = next(x for x in capas if x["id"] == f["id"])
        g = lectura[f["id"]]
        dec = decisiones.get("capas", {}).get(f["clave"], {})
        crs, origen_crs = H.resolver_crs(c, g, dec)
        crs_doc.append({"capa": f["clave"], "crs_origen": crs.to_string() if crs else "", "epsg_origen": crs.to_epsg() if crs else None,
                        "como_se_determino": origen_crs, "crs_destino": f"EPSG:{cat.srid}", "sugerencia": c.get("sugerencia_crs", "")})
        if crs is None:
            f["estado"] = "PENDIENTE (sistema de referencia)"
            pendientes.append(f"{f['clave']}: sistema de referencia no declarado ({c.get('sugerencia_crs', '')})")
            observar("CRÍTICO", c["archivo"], c["capa"], "CRS", "Sistema de referencia no declarado", "Estructura intermedia: SRID 9377",
                     f"No se asume el CRS. Indicio: {c.get('sugerencia_crs', '')}", "Indicar crs_origen en decisiones.json > capas")
            continue
        g = g.set_crs(crs, allow_override=True)
        destino = f["destino_final"]
        familia = "poligono" if destino in ("_limite_municipal",) else H.FAMILIA[next(col["geometria"] for col in cat.intermedia["tablas"][destino] if col["geometria"])]
        try:
            preparadas[f["id"]] = H.preparar_geometrias(g, familia, cat.srid, transformaciones, f["clave"])
        except Exception as e:  # noqa: BLE001
            log.error("Fallo preparando %s: %s", f["clave"], traceback.format_exc())
            f["estado"] = "ERROR (geometría)"
            observar("ALTO", c["archivo"], c["capa"], "geometria", "Error al transformar", "Motor de transformación", str(e), "Revisar la capa")

    # límite municipal
    lim_ids = [f["id"] for f in clasif if f["destino_final"] == "_limite_municipal" and f["id"] in preparadas]
    limite = preparadas[lim_ids[0]] if lim_ids else None
    if len(lim_ids) > 1:
        observar("MEDIO", "", "", "límite", "Varias capas de límite municipal", "Toolkit", "Se usa la primera", "Indicar cuál usar (excluir las demás)")
    if limite is None:
        observar("MEDIO", "", "", "límite municipal", "Sin capa de límite municipal", "Toolkit (G3/G4)",
                 "No se pueden evaluar extensión ni cobertura total", "Aportar el límite oficial (IGAC/DANE MGN)")

    # ---------------------------------------------------------------- 5. equivalencias semánticas
    equivalencias = []
    por_destino: dict[str, list] = {}
    for f in clasif:
        if f["id"] in preparadas and f["destino_final"] not in (None, "_limite_municipal"):
            por_destino.setdefault(f["destino_final"], []).append(f)
    for destino, grupo in por_destino.items():
        if len(grupo) < 2 or destino in COMPLEMENTARIAS:
            continue
        for i in range(len(grupo)):
            for j in range(i + 1, len(grupo)):
                a, b = preparadas[grupo[i]["id"]], preparadas[grupo[j]["id"]]
                ua, ub = shapely.union_all(a.geometry.values), shapely.union_all(b.geometry.values)
                inter = shapely.intersection(ua, ub).area
                ratio = inter / max(1e-9, min(ua.area, ub.area))
                equivalencias.append({"destino": destino, "capa_a": grupo[i]["clave"], "capa_b": grupo[j]["clave"],
                                      "registros_a": len(a), "registros_b": len(b), "area_a_ha": round(ua.area / 1e4, 2),
                                      "area_b_ha": round(ub.area / 1e4, 2), "superposicion_relativa": round(ratio, 3),
                                      "interpretacion": "POSIBLES EQUIVALENTES (no se fusionan)" if ratio > 0.5 else "Complementarias (se anexan)"})
                if ratio > 0.5:
                    for f in (grupo[i], grupo[j]):
                        if not f["estado"].startswith("CONFIRMADA"):
                            f["estado"] = "PENDIENTE (posibles capas equivalentes)"
                    pendientes.append(f"{destino}: '{grupo[i]['clave']}' y '{grupo[j]['clave']}' representan el mismo fenómeno ({ratio:.0%} de superposición); elegir una")
                    observar("ALTO", grupo[i]["archivo"], f"{grupo[i]['capa']} | {grupo[j]['clave']}", "capa",
                             "Posibles capas equivalentes", "Inventario (equivalencias semánticas)",
                             f"Superposición relativa {ratio:.0%}; no se fusionan automáticamente",
                             "Elegir una (la otra 'excluir') en decisiones.json > capas, según fecha, fuente y escala")

    # ---------------------------------------------------------------- 6. homologación y estructura intermedia
    tablas: dict[str, list] = {t: [] for t in cat.intermedia["tablas"] if t != "municipio"}
    mapeos, traz, sin_mapear = [], [], {}
    for f in clasif:
        d = f["destino_final"]
        if f["id"] not in preparadas or d in (None, "_limite_municipal") or f["estado"].startswith(("PENDIENTE", "ERROR")):
            continue
        c = next(x for x in capas if x["id"] == f["id"])
        try:
            res, mapeo = H.homologar_capa(c, preparadas[f["id"]], d, cat, reglas, indices, proyecto, decisiones, valores_log)
            for m in mapeo:
                mapeos.append({"capa": f["clave"], "tabla_destino": d, **m})
                if m["obligatorio"] and not m["campo_origen"]:
                    sin_mapear.setdefault(f["clave"], {})[m["columna_destino"]] = None
                    observar("ALTO", c["archivo"], c["capa"], m["columna_destino"], "Campo obligatorio sin correspondencia",
                             "Oficial script 1 (NOT NULL)", f"Tabla {d}", "Mapear en decisiones.json > campos o > constantes")
            tablas[d].append(res)
            f["estado"] = f["estado"] + " → CARGADA"
        except Exception as e:  # noqa: BLE001
            log.error("Fallo homologando %s: %s", f["clave"], traceback.format_exc())
            observar("ALTO", c["archivo"], c["capa"], "", "Error de homologación", "Motor de homologación", str(e), "Revisar la capa")
    final: dict[str, gpd.GeoDataFrame] = {}
    for t, partes in tablas.items():
        if not partes:
            final[t] = None
            continue
        g = gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), crs=cat.srid)
        # identificadores: se conservan si vienen únicos y completos; si no, se generan (trazabilidad en zz_trazabilidad_origen)
        if "identificador" in g and g["identificador"].notna().all() and not g["identificador"].astype(str).duplicated().any():
            metodo_id = "conservado de la fuente"
        else:
            g["identificador"] = [f"{dane}_{ABREV[t]}_{i + 1:06d}" for i in range(len(g))]
            metodo_id = "generado por el toolkit"
        for _, r in g.iterrows():
            traz.append({"tabla": t, "identificador": r["identificador"], "capa_origen": r["_capa_origen"],
                         "fid_origen": int(r["_fid_origen"]), "metodo_identificador": metodo_id})
        final[t] = g.drop(columns=["_capa_origen", "_fid_origen"])
    municipio = pd.DataFrame([{k: mun.get(k) for k in ("codigo_departamento", "codigo_municipio", "nombre_municipio",
                                                       "tipo_interesado", "tipo_documento", "numero_documento")}])
    if not mun:
        observar("CRÍTICO", "", "municipio", "", "Datos del municipio no suministrados", "Oficial script 1 (municipio)",
                 str(detectar_municipio(capas, lectura)), "Diligenciar proyecto.json > municipio")
    for n in ("tipo_interesado", "tipo_documento"):
        idx = indices.get(("municipio", n))
        if idx and municipio[n].iloc[0] and municipio[n].iloc[0] not in {c for c, _ in idx.hojas}:
            cod, _, _ = idx.homologar(municipio[n].iloc[0])
            municipio.loc[0, n] = cod
    traz_df = pd.DataFrame(traz, columns=["tabla", "identificador", "capa_origen", "fid_origen", "metodo_identificador"])

    nombre_gpkg = f"estructura_intermedia_LADM_COL_POT_{dane}.gpkg"
    gpkg = rutas["04"] / nombre_gpkg
    S.escribir_gpkg_intermedio(gpkg, final, municipio, cat, traz_df)
    S.copiar_modelo(cat, rutas["06"] / "modelo_oficial_usado")
    S.guion_fase4(rutas["04"] / "fase4_migracion", cat, nombre_gpkg)
    # 03: copias de trabajo y capas homologadas
    for f in clasif:
        if f["id"] in preparadas:
            capa_nom = normalizar(f"{f['id']}_{f['archivo'].rsplit('.', 1)[0]}_{f['capa'] or ''}")[:60]
            preparadas[f["id"]].to_file(rutas["03"] / "capas_transformadas_EPSG9377.gpkg", layer=capa_nom, engine="pyogrio")
    for t, g in final.items():
        if g is not None:
            g.to_file(rutas["03"] / "capas_homologadas.gpkg", layer=t, engine="pyogrio")
    cl = pd.DataFrame(clasif)
    vals_df = H.agregar_registros_valores(valores_log)
    for v in vals_df.itertuples():
        if pd.isna(v.valor_homologado) and v.metodo not in ("vacio",):
            pendientes.append(f"{v.tabla}.{v.columna}: valor '{v.valor_origen}' ({v.n_registros} reg.) sin homologar – {v.metodo}"
                              + (f"; sugerencias: {v.sugerencias}" if v.sugerencias else ""))
            observar("ALTO", v.capa.split("::")[0], v.capa.split("::")[1], f"{v.tabla}.{v.columna}", f"Valor '{v.valor_origen}' sin homologar",
                     "Homologación de dominios (coincidencia exacta)", f"{v.metodo}. Sugerencias: {v.sugerencias or 'ninguna'}",
                     "Registrar en decisiones.json > valores con el código oficial")
    S.excel(rutas["03"] / "matriz_homologacion.xlsx", {
        "clasificacion_capas": cl, "campos": pd.DataFrame(mapeos), "valores_dominio": vals_df, "identificadores": traz_df})

    # ---------------------------------------------------------------- 7. validación
    interlis = interlis or {}
    try:
        resultados = V.validar(final, municipio, cat, indices, limite, interlis)
    except Exception as e:  # noqa: BLE001  (no detener la entrega)
        log.error("Validación interrumpida: %s", traceback.format_exc())
        resultados = [V.Resultado("X0", "Estructural", "Toolkit", "Motor de validación", "", "NO_EJECUTADA", "CRÍTICO", 0, 1,
                                  [{"identificador": "", "campo": "", "problema": f"Error interno del validador: {e}", "valor": ""}])]
    cumplimiento = V.resumen_cumplimiento(resultados)
    reglas_df = pd.DataFrame([{k: getattr(r, k) for k in ("id", "componente", "origen", "descripcion", "tabla", "estado", "severidad", "n_evaluados", "n_errores")} for r in resultados])
    traz_idx = traz_df.set_index("identificador")["capa_origen"].to_dict() if len(traz_df) else {}
    for r in resultados:
        for d in r.detalles:
            if r.estado in ("FALLA", "CON_ADVERTENCIAS", "SIN_DATOS", "NO_EJECUTADA"):
                origen = traz_idx.get(str(d.get("identificador", "")).split(" / ")[0], "")
                observar(r.severidad or ("MEDIO" if r.estado == "NO_EJECUTADA" else "BAJO"), origen.split("::")[0], r.tabla,
                         d.get("campo", ""), d.get("problema", ""), f"{r.id} – {r.origen}",
                         f"{r.descripcion}. Identificador: {d.get('identificador', '')} {d.get('valor', '') or ''}".strip(), _sol(d.get("problema", "")))
    por_comp = {comp: reglas_df[reglas_df.componente == comp] for comp in reglas_df.componente.unique()}
    nombres_hoja = {"Estructural": "validacion_estructura", "Semántica": "validacion_atributos_dominios", "Espacial": "validacion_geometrias_topologia",
                    "Relacional": "validacion_relaciones", "Documental": "validacion_documental", "INTERLIS": "validacion_interlis"}
    for comp, df in por_comp.items():
        det = pd.DataFrame([{"regla": r.id, "tabla": r.tabla, **d} for r in resultados if r.componente == comp for d in r.detalles])
        S.excel(rutas["07"] / f"{nombres_hoja[comp]}.xlsx", {"reglas": df, "detalle": det})
    obs_df = pd.DataFrame(obs)
    orden = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}
    obs_df = obs_df.sort_values("severidad", key=lambda s: s.map(orden)).reset_index(drop=True)
    obs_df.insert(0, "n", range(1, len(obs_df) + 1))
    S.excel(rutas["07"] / "errores_advertencias_pendientes.xlsx", {
        "criticos_y_altos": obs_df[obs_df.severidad.isin(["CRÍTICO", "ALTO"])],
        "advertencias": obs_df[obs_df.severidad.isin(["MEDIO", "BAJO"])],
        "pendientes": pd.DataFrame({"pendiente": pendientes})})

    # ---------------------------------------------------------------- 8. documentación técnica
    filas_dic = []
    for t, cols in cat.intermedia["tablas"].items():
        for col in cols:
            dom = indices.get((t, col["nombre"]))
            filas_dic.append({"tabla": t, "columna": col["nombre"], "tipo_sql_oficial": col["tipo_sql"], "obligatorio": col["obligatorio"],
                              "dominio": dom.dominio.nombre if dom else "", "valores_permitidos": " | ".join(c for c, _ in dom.hojas) if dom else ""})
    dom_rows = [{"dominio": n, "ilicode": c, "dispName": s} for n, d in cat.dominios.items() for c, s in d.hojas()]
    clases_rows = [{"clase": n, "modelo": c.modelo, "topic": c.topic, "extiende": c.extiende, "abstracta": c.abstracta,
                    "atributo": a.nombre, "tipo": a.tipo, "obligatorio": a.obligatorio} for n, c in cat.clases.items() for a in (c.atributos or [None]) if a] \
        + [{"clase": n, "modelo": c.modelo, "topic": c.topic, "extiende": c.extiende, "abstracta": c.abstracta, "atributo": "", "tipo": "", "obligatorio": ""}
           for n, c in cat.clases.items() if not c.atributos]
    S.excel(rutas["06"] / "diccionario_datos_y_catalogo_modelo.xlsx", {
        "estructura_intermedia": pd.DataFrame(filas_dic), "dominios": pd.DataFrame(dom_rows), "clases_atributos": pd.DataFrame(clases_rows),
        "asociaciones": pd.DataFrame([{"asociacion": a["nombre"], **r} for a in cat.asociaciones for r in a["roles"]]),
        "correspondencia_clases": correspondencia_clases(cat)})
    cat.exportar_json(rutas["06"] / "catalogo_modelo_LADM_COL_POT.json")
    S.excel(rutas["06"] / "transformaciones_y_sistemas_referencia.xlsx", {
        "sistemas_referencia": pd.DataFrame(crs_doc), "transformaciones": pd.DataFrame(transformaciones),
        "comprimidos": pd.DataFrame(eventos_zip)})
    metadatos = {"municipio": mun, "fecha_procesamiento": t0.isoformat(timespec="seconds"), "srid": cat.srid,
                 "modelo": cat.resumen()["modelos"], "datos_de_prueba": prueba,
                 "capas": [{"clave": f["clave"], "destino": f["destino_final"], "estado": f["estado"],
                            **{k: next(x for x in capas if x["id"] == f["id"]).get(k) for k in ("formato", "n_registros", "crs", "bbox", "fuente_procedencia")}}
                           for f in clasif],
                 "nota": "Metadatos de procesamiento (no reemplazan los metadatos ISO 19115/NTC 4611 de cada producto)."}
    (rutas["06"] / "metadatos_procesamiento.json").write_text(json.dumps(metadatos, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # ---------------------------------------------------------------- 9. inventario (con clasificación)
    inv = pd.DataFrame([{k: v for k, v in c.items() if k not in ("campos", "crs_wkt")} for c in capas])
    if len(cl):
        inv = inv.merge(cl[["id", "destino_sugerido", "confianza", "estado"]], on="id", how="left")
    campos = pd.DataFrame([{"id": c["id"], "archivo": c["archivo"], "capa": c.get("capa", ""), **f} for c in capas for f in c.get("campos", [])])
    S.excel(rutas["02"] / "inventario_cartografico.xlsx", {
        "inventario_general": inv, "diccionario_atributos_origen": campos, "archivos_recibidos": pd.DataFrame(archivos),
        "sistemas_referencia": inv[[c for c in ("id", "archivo", "capa", "crs", "epsg", "sugerencia_crs") if c in inv.columns]] if len(inv) else inv,
        "equivalencias_y_duplicados": pd.DataFrame(equivalencias)})

    # ---------------------------------------------------------------- 10. cartografía temática de control
    try:
        hechas = S.vistas_previas(rutas["05"], {k: v for k, v in final.items() if v is not None}, limite)
        log.info("Vistas de control: %s", hechas)
    except Exception:  # noqa: BLE001
        log.error("Vistas de control: %s", traceback.format_exc())

    # ---------------------------------------------------------------- 11. reportes
    plantilla = {"_instrucciones": "Revise, ajuste y guarde como decisiones.json; luego vuelva a ejecutar con --decisiones. "
                                   "Use SOLO códigos oficiales (ver 06_DOCUMENTACION_TECNICA/diccionario_datos_y_catalogo_modelo.xlsx).",
                 "capas": {}, "campos": {}, "valores": {}, "constantes": {}}
    for f in clasif:
        if f["estado"].startswith("PENDIENTE"):
            plantilla["capas"][f["clave"]] = {"destino": f["destino_sugerido"], "_estado": f["estado"], "_alternativas": f["alternativas"]}
            if "sistema de referencia" in f["estado"]:
                c = next(x for x in capas if x["id"] == f["id"])
                plantilla["capas"][f["clave"]]["crs_origen"] = None
                plantilla["capas"][f["clave"]]["_indicio_crs"] = c.get("sugerencia_crs", "")
    for clave, cols in sin_mapear.items():
        plantilla["constantes"][clave] = {**cols, "_nota": "Columnas obligatorias sin campo de origen: indique un valor constante (código oficial) o mapee un campo en 'campos'"}
    for v in vals_df.itertuples():
        if pd.isna(v.valor_homologado) and v.metodo != "vacio":
            plantilla["valores"].setdefault(f"{v.tabla}.{v.columna}", {})[v.valor_origen] = (str(v.sugerencias).split(", ")[0] if isinstance(v.sugerencias, str) and v.sugerencias else None)
    (rutas["08"] / "decisiones_pendientes.json").write_text(json.dumps(plantilla, ensure_ascii=False, indent=2), encoding="utf-8")
    sev = Counter(obs_df["severidad"]) if len(obs_df) else Counter()
    ctx = {
        "municipio": mun.get("nombre_municipio") or "(sin identificar)", "departamento": mun.get("departamento") or "", "dane": dane,
        "instrumento": proyecto.get("fuente_administrativa", {}).get("fuente_administrativa_tipo_pot") or "(sin definir)",
        "modelo": ", ".join(f"{m['modelo']} v{m['version']}" for m in cat.resumen()["modelos"]),
        "fecha": t0.strftime("%Y-%m-%d %H:%M"), "prueba": prueba,
        "n_archivos": len(archivos), "n_capas": len(capas), "n_vectoriales": sum(c["categoria"] == "vector" for c in capas),
        "n_clasificadas": sum(1 for f in clasif if f["destino_sugerido"]), "n_cargadas": sum("CARGADA" in f["estado"] for f in clasif),
        "n_pendientes_capa": sum(f["estado"].startswith("PENDIENTE") for f in clasif),
        "n_tablas_con_datos": sum(1 for g in final.values() if g is not None) + (1 if mun else 0), "n_tablas": len(cat.intermedia["tablas"]),
        "severidades": sev, "registros_por_tabla": {t: (0 if g is None else len(g)) for t, g in final.items()} | {"municipio": len(municipio) if mun else 0},
        "resumen_cumplimiento": cumplimiento, "pendientes": pendientes,
        "limitaciones": [
            "La validación INTERLIS (XTF + ilivalidator) no se ejecuta en este entorno: requiere PostgreSQL/PostGIS, el ETL oficial y Java (ver 04/fase4_migracion).",
            "La clasificación de capas es heurística (nombre, campos y valores); solo se carga automáticamente con confianza ALTA.",
            "Los valores de dominio solo se asignan con coincidencia exacta normalizada o por decisión del usuario.",
            "La existencia de los códigos en DIVIPOLA no se verifica contra la tabla oficial del DANE.",
            "Los rásteres y documentos se inventarían, pero no se integran a la estructura intermedia (el modelo no los contiene).",
            "Las vistas de 05_CARTOGRAFIA_TEMATICA son de control de calidad; no son cartografía oficial ni planos protocolizables.",
        ] + (["PAQUETE GENERADO CON DATOS SINTÉTICOS DE PRUEBA."] if prueba else []),
    }
    S.informe_md(rutas["08"] / "informe_general_procesamiento.md", ctx)
    resumen_capas = cl.merge(inv[["id", "formato", "n_registros", "crs"]], on="id", how="left") if len(cl) else cl
    S.excel(rutas["08"] / "reportes_procesamiento.xlsx", {
        "cumplimiento_por_componente": cumplimiento, "reglas_evaluadas": reglas_df, "matriz_inconsistencias": obs_df,
        "resumen_capas": resumen_capas, "registro_transformaciones": pd.DataFrame(transformaciones)})

    # ---------------------------------------------------------------- 12. entrega final
    shutil.copy2(gpkg, rutas["09"] / gpkg.name)
    for p in (rutas["08"] / "informe_general_procesamiento.md", rutas["08"] / "informe_general_procesamiento.html",
              rutas["07"] / "errores_advertencias_pendientes.xlsx", rutas["06"] / "diccionario_datos_y_catalogo_modelo.xlsx"):
        shutil.copy2(p, rutas["09"] / p.name)
    shutil.copytree(rutas["04"] / "fase4_migracion", rutas["09"] / "fase4_migracion", dirs_exist_ok=True)
    shutil.rmtree(trabajo, ignore_errors=True)
    log.info("Fin del procesamiento en %.1f s", (dt.datetime.now() - t0).total_seconds())
    for h in list(log.handlers):
        h.flush()
    man = S.manifiesto(raiz)
    man.to_csv(rutas["09"] / "manifiesto_archivos.csv", index=False)
    zip_path = rutas["09"] / f"{raiz.name}.zip"
    S.comprimir(raiz, zip_path)
    log.info("ZIP: %s (%.1f MB)", zip_path, zip_path.stat().st_size / 1e6)
    return raiz


def main(argv=None):
    ap = argparse.ArgumentParser(description="Automatización y estructuración LADM_COL-POT (estructura intermedia oficial)")
    ap.add_argument("--insumos", nargs="+", required=True, type=Path, help="Carpeta(s) con los insumos del municipio")
    ap.add_argument("--salida", required=True, type=Path)
    ap.add_argument("--proyecto", type=Path, help="proyecto.json (municipio y fuentes)")
    ap.add_argument("--decisiones", type=Path, help="decisiones.json (destinos, CRS, campos, valores)")
    ap.add_argument("--modelo", type=Path, default=BASE / "modelo_oficial")
    ap.add_argument("--reglas", type=Path, default=BASE / "config" / "reglas_clasificacion.json")
    ap.add_argument("--prueba", action="store_true", help="Marca el paquete como generado con datos de prueba")
    ap.add_argument("--xtf", help="XTF ya generado (fase 4) para validar con ilivalidator")
    ap.add_argument("--ilivalidator", help="Ruta a ilivalidator.jar")
    a = ap.parse_args(argv)
    raiz = ejecutar(a.insumos, a.salida, a.proyecto, a.decisiones, a.modelo, a.reglas, a.prueba,
                    {"xtf": a.xtf, "ilivalidator_jar": a.ilivalidator, "modeldir": str(a.modelo), "log": str(a.salida / "ilivalidator.log")})
    print(f"\nPaquete generado: {raiz}")


if __name__ == "__main__":
    main()
