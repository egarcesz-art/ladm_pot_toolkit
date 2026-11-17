"""Lectura del modelo oficial LADM_COL-POT.

Construye el catálogo (dominios, clases, atributos, asociaciones y estructura
intermedia) EXCLUSIVAMENTE a partir de los archivos oficiales de la carpeta
`modelo_oficial/`. No contiene clases, atributos ni dominios escritos a mano:
si se reemplazan los archivos por una versión posterior, el catálogo cambia.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def normalizar(texto) -> str:
    """Mayúsculas, sin tildes, separadores unificados a '_' (para comparar)."""
    if texto is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^0-9A-Za-z]+", "_", t).strip("_").upper()
    return re.sub(r"_+", "_", t)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Parser INTERLIS 2.3 (subconjunto necesario: DOMAIN de enumeración, CLASS,
# STRUCTURE, ASSOCIATION, atributos y MANDATORY)
# --------------------------------------------------------------------------

@dataclass
class Dominio:
    nombre: str              # p. ej. POT_ClasificacionSueloTipo
    modelo: str
    arbol: list               # [(codigo, dispName, [hijos])]
    extiende: str | None = None

    def hojas(self) -> list[tuple[str, str]]:
        """(ilicode completo 'Padre.Hijo', dispName) de los valores hoja."""
        out = []

        def rec(nodos, prefijo):
            for cod, disp, hijos in nodos:
                full = f"{prefijo}.{cod}" if prefijo else cod
                if hijos:
                    rec(hijos, full)
                else:
                    out.append((full, disp or cod))
        rec(self.arbol, "")
        return out

    def nodos_intermedios(self) -> list[str]:
        out = []

        def rec(nodos, prefijo):
            for cod, _d, hijos in nodos:
                full = f"{prefijo}.{cod}" if prefijo else cod
                if hijos:
                    out.append(full)
                    rec(hijos, full)
        rec(self.arbol, "")
        return out


@dataclass
class Atributo:
    nombre: str
    tipo: str
    obligatorio: bool
    extendido: bool = False


@dataclass
class Clase:
    nombre: str
    modelo: str
    topic: str | None
    extiende: str | None
    abstracta: bool
    es_estructura: bool
    atributos: list = field(default_factory=list)
    restricciones: list = field(default_factory=list)


def _limpiar_ili(texto: str) -> str:
    # conserva !!@ ili2db.dispName para enumeraciones; elimina otros comentarios
    texto = re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)
    lineas = []
    for ln in texto.splitlines():
        s = ln.strip()
        if s.startswith("!!@"):
            m = re.search(r'ili2db\.dispName\s*=\s*"?([^"]+?)"?\s*$', s)
            if m:
                lineas.append(f'@DISP "{m.group(1)}"')
            continue
        if "!!" in ln:
            ln = ln.split("!!")[0]
        lineas.append(ln)
    return "\n".join(lineas)


def _parse_enum(cuerpo: str):
    """Parsea '(A, B(C, D), E)' con @DISP previos -> árbol."""
    tokens = re.findall(r'@DISP "[^"]*"|[A-Za-z_][A-Za-z0-9_]*|[(),]|\.\.\.', cuerpo)
    pos = 0

    def lista():
        nonlocal pos
        assert tokens[pos] == "("
        pos += 1
        nodos, disp = [], None
        while pos < len(tokens):
            t = tokens[pos]
            if t.startswith("@DISP"):
                disp = t[7:-1]
                pos += 1
            elif t == ")":
                pos += 1
                return nodos
            elif t in (",", "..."):
                pos += 1
            else:
                cod = t
                pos += 1
                hijos = []
                if pos < len(tokens) and tokens[pos] == "(":
                    hijos = lista()
                nodos.append([cod, disp, hijos])
                disp = None
        return nodos
    return lista()


def _bloque_parentesis(texto: str, inicio: int) -> tuple[str, int]:
    nivel, i = 0, inicio
    while i < len(texto):
        if texto[i] == "(":
            nivel += 1
        elif texto[i] == ")":
            nivel -= 1
            if nivel == 0:
                return texto[inicio:i + 1], i + 1
        i += 1
    raise ValueError("Paréntesis no balanceados en el modelo")


def parsear_ili(path: Path) -> dict:
    texto = _limpiar_ili(path.read_text(encoding="utf-8", errors="replace"))
    m = re.search(r'MODEL\s+(\w+)\s*(?:\(\w+\))?.*?VERSION\s+"([^"]+)"', texto, re.S)
    modelo, version = (m.group(1), m.group(2)) if m else (path.stem, "?")
    dominios, clases, asociaciones = {}, {}, []

    # ---- dominios de enumeración (en DOMAIN global o dentro de TOPIC)
    for md in re.finditer(r"\b(\w+)\s*(?:\(\s*(?:ABSTRACT|FINAL)\s*\))?\s*(?:EXTENDS\s+([\w.]+)\s*)?=\s*\(", texto):
        nombre, ext = md.group(1), md.group(2)
        if nombre in ("CLASS", "STRUCTURE", "ASSOCIATION", "TOPIC", "MODEL"):
            continue
        previo = texto[max(0, md.start() - 40):md.start()]
        if re.search(r"\b(CLASS|STRUCTURE|ASSOCIATION)\s*$", previo):
            continue
        cuerpo, _ = _bloque_parentesis(texto, md.end() - 1)
        if not re.match(r"\(\s*(@DISP|[A-Za-z_])", cuerpo):
            continue
        try:
            arbol = _parse_enum(cuerpo)
        except Exception:
            continue
        dominios[nombre] = Dominio(nombre, modelo, arbol, ext)

    # ---- clases / estructuras
    topic_actual = None
    patron = re.compile(r"\bTOPIC\s+(\w+)|\b(CLASS|STRUCTURE)\s+(\w+)\s*(\((?:ABSTRACT|EXTENDED|FINAL)\))?\s*(?:EXTENDS\s+([\w.]+)\s*)?=(.*?)\bEND\s+\3\s*;", re.S)
    for mc in patron.finditer(texto):
        if mc.group(1):
            topic_actual = mc.group(1)
            continue
        tipo, nombre, mod, ext, cuerpo = mc.group(2), mc.group(3), mc.group(4) or "", mc.group(5), mc.group(6)
        c = Clase(nombre, modelo, topic_actual, ext, "ABSTRACT" in mod, tipo == "STRUCTURE")
        for ma in re.finditer(r"^\s*(\w+)\s*(\(EXTENDED\))?\s*:\s*(MANDATORY\s+)?([^;]+);", cuerpo, re.M):
            if ma.group(1) in ("MANDATORY", "UNIQUE", "CONSTRAINT", "SET"):
                continue
            c.atributos.append(Atributo(ma.group(1), " ".join(ma.group(4).split()), bool(ma.group(3)), bool(ma.group(2))))
        for mr in re.finditer(r"MANDATORY\s+CONSTRAINT\s+([^;]+);", cuerpo):
            c.restricciones.append(" ".join(mr.group(1).split()))
        clases[nombre] = c

    for ma in re.finditer(r"ASSOCIATION\s+(\w+)\s*=(.*?)END\s+\1\s*;", texto, re.S):
        roles = re.findall(r"(\w+)\s*--\s*\{([^}]+)\}\s*([\w.]+)", ma.group(2))
        asociaciones.append({"nombre": ma.group(1), "roles": [{"rol": r, "cardinalidad": c, "clase": k} for r, c, k in roles]})

    return {"modelo": modelo, "version": version, "archivo": path.name, "sha256": sha256(path),
            "dominios": dominios, "clases": clases, "asociaciones": asociaciones}


# --------------------------------------------------------------------------
# Estructura intermedia oficial (SQL) y reglas de dominio del script 2
# --------------------------------------------------------------------------

def parsear_estructura_intermedia(sql_path: Path) -> dict:
    sql = sql_path.read_text(encoding="utf-8", errors="replace")
    sql = re.sub(r"--[^\n]*", "", sql)
    tablas = {}
    for mt in re.finditer(r"CREATE TABLE\s+(\w+)\s*\((.*?)\);", sql, re.S | re.I):
        cols = []
        for linea in re.split(r",\s*\n", mt.group(2)):
            s = " ".join(linea.split()).rstrip(",")
            mcol = re.match(r"(\w+)\s+(.+?)(\s+NOT NULL|\s+NULL)?$", s, re.I)
            if not mcol:
                continue
            nombre, tipo, nul = mcol.group(1), mcol.group(2).strip(), (mcol.group(3) or "").strip().upper()
            geom = re.search(r"geometry\((\w+),\s*(\d+)\)", tipo, re.I)
            largo = re.search(r"varchar\((\d+)\)", tipo, re.I)
            cols.append({
                "nombre": nombre,
                "tipo_sql": tipo,
                "obligatorio": nul == "NOT NULL",
                "geometria": geom.group(1).lower() if geom else None,
                "srid": int(geom.group(2)) if geom else None,
                "longitud": int(largo.group(1)) if largo else None,
            })
        tablas[mt.group(1)] = cols
    srid = re.search(r"INSERT into spatial_ref_sys.*?values\s*\(\s*(\d+)", sql, re.S | re.I)
    return {"tablas": tablas, "srid": int(srid.group(1)) if srid else None}


def parsear_reglas_dominio(sql_path: Path) -> list[dict]:
    """Extrae del script oficial 2 las parejas (tabla, columna) -> tabla de dominio."""
    sql = sql_path.read_text(encoding="utf-8", errors="replace")
    reglas = []
    for bloque in re.split(r";\s*\n", sql):
        mt = re.search(r"from\s+(\w+)\s+(?:as\s+)?dt\b", bloque, re.I)
        md = re.search(r"dt\.(\w+)\s+not in\s*\(\s*select\s+ilicode\s+from\s+(\w+)(.*?)\)", bloque, re.I | re.S)
        msg = re.search(r"'([^']+)'\s+as\s+mensaje", bloque, re.I)
        if mt and md:
            thisclass = re.search(r"thisclass\s+like\s+'([^']+)'", md.group(3) or "")
            reglas.append({"tabla": mt.group(1), "columna": md.group(1), "tabla_dominio": md.group(2),
                           "thisclass": thisclass.group(1) if thisclass else None,
                           "mensaje_oficial": msg.group(1) if msg else ""})
    return reglas


def tablas_requeridas_etl(sql_path: Path) -> list[str]:
    """Tablas del esquema LADM_COL-POT (ili2db) que el script 4 espera encontrar."""
    sql = sql_path.read_text(encoding="utf-8", errors="replace")
    nombres = set(re.findall(r"insert into\s+(\w+)", sql, re.I))
    nombres |= set(re.findall(r"from\s+((?:pot|col|t_ili2db)\w*)", sql, re.I))
    return sorted(n.lower() for n in nombres)


# --------------------------------------------------------------------------
# Catálogo integrado
# --------------------------------------------------------------------------

class Catalogo:
    def __init__(self, carpeta_modelo: Path):
        self.carpeta = Path(carpeta_modelo)
        ilis = sorted(self.carpeta.glob("*.ili"))
        if not ilis:
            raise FileNotFoundError(f"No hay archivos .ili en {self.carpeta}")
        self.modelos = [parsear_ili(p) for p in ilis]
        self.dominios: dict[str, Dominio] = {}
        self.clases: dict[str, Clase] = {}
        self.asociaciones = []
        for m in self.modelos:
            self.dominios.update(m["dominios"])
            self.clases.update(m["clases"])
            self.asociaciones += m["asociaciones"]
        self._resolver_extensiones()
        ei = self.carpeta / "ESTRUCTURA_INTERMEDIA"
        self.intermedia = parsear_estructura_intermedia(ei / "1_create_intermediate_structure.sql")
        self.reglas_dominio = parsear_reglas_dominio(ei / "2_validate_intermediate_structure_data.sql")
        self.tablas_etl = tablas_requeridas_etl(ei / "4_etl_intermediate_structure_to_ladm_col_pot.sql")
        # Complemento: columnas con dominio que solo aparecen en el ETL oficial (p. ej. municipio)
        cubiertas = {(r["tabla"], r["columna"]) for r in self.reglas_dominio}
        etl = (ei / "4_etl_intermediate_structure_to_ladm_col_pot.sql").read_text(encoding="utf-8", errors="replace")
        for bloque in re.split(r";\s*\n", etl):
            alias = {a: t for t, a in re.findall(r"(?:from|join)\s+(\w+)\s+(?:as\s+)?(\w+)", bloque, re.I)}
            for dom, al, col in re.findall(r"select\s+t_id\s+from\s+(\w+)\s+where\s+ilicode\s+like\s+(\w+)\.(\w+)", bloque, re.I):
                tabla = alias.get(al, al)
                if tabla in self.intermedia["tablas"] and (tabla, col) not in cubiertas:
                    self.reglas_dominio.append({"tabla": tabla, "columna": col, "tabla_dominio": dom, "thisclass": None,
                                                "mensaje_oficial": f"Valor de {col} no homologable con {dom} (derivado del ETL oficial)"})
                    cubiertas.add((tabla, col))
        self.srid = self.intermedia["srid"]

    def _resolver_extensiones(self):
        for d in list(self.dominios.values()):
            if d.extiende:
                base = self.dominios.get(d.extiende.split(".")[-1])
                if base:
                    import copy
                    arbol = copy.deepcopy(base.arbol)
                    for cod, disp, hijos in d.arbol:
                        existente = next((n for n in arbol if n[0] == cod), None)
                        if existente:
                            existente[2] = hijos or existente[2]
                        else:
                            arbol.append([cod, disp, hijos])
                    d.arbol = arbol

    # dominio ILI correspondiente a una tabla de dominio ili2db (nombre en minúsculas)
    def dominio_de_tabla(self, tabla_dominio: str, thisclass: str | None = None) -> Dominio | None:
        if thisclass:
            d = self.dominios.get(thisclass.split(".")[-1])
            if d:
                return d
        for nombre, d in self.dominios.items():
            if nombre.lower() == tabla_dominio.lower():
                return d
        return None

    def dominios_por_columna(self) -> dict[tuple[str, str], Dominio]:
        out = {}
        for r in self.reglas_dominio:
            d = self.dominio_de_tabla(r["tabla_dominio"], r["thisclass"])
            if d:
                out[(r["tabla"], r["columna"])] = d
        return out

    def resumen(self) -> dict:
        return {
            "modelos": [{"modelo": m["modelo"], "version": m["version"], "archivo": m["archivo"], "sha256": m["sha256"]} for m in self.modelos],
            "n_dominios": len(self.dominios),
            "n_clases": len(self.clases),
            "tablas_intermedias": list(self.intermedia["tablas"]),
            "srid": self.srid,
            "reglas_dominio": len(self.reglas_dominio),
        }

    def exportar_json(self, path: Path):
        data = {
            "resumen": self.resumen(),
            "dominios": {n: {"modelo": d.modelo, "extiende": d.extiende, "valores": [{"ilicode": c, "dispName": s} for c, s in d.hojas()],
                             "nodos_no_hoja": d.nodos_intermedios()} for n, d in self.dominios.items()},
            "clases": {n: {"modelo": c.modelo, "topic": c.topic, "extiende": c.extiende, "abstracta": c.abstracta, "estructura": c.es_estructura,
                           "atributos": [a.__dict__ for a in c.atributos], "restricciones": c.restricciones} for n, c in self.clases.items()},
            "asociaciones": self.asociaciones,
            "estructura_intermedia": self.intermedia,
            "reglas_dominio_script2": self.reglas_dominio,
            "tablas_esperadas_por_etl": self.tablas_etl,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
