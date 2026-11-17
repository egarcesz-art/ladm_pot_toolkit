"""Regenera docs/REFERENCIA_TECNICA_MODELO.md y el catálogo JSON desde modelo_oficial/ (ejecutar tras actualizar el modelo)."""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from ladm_pot.modelo import Catalogo  # noqa: E402

cat = Catalogo(BASE / "modelo_oficial")
idx = cat.dominios_por_columna()
L = ["# Referencia técnica – catálogo generado desde los archivos oficiales", "",
     "Generado automáticamente desde `modelo_oficial/` con `python docs/generar_referencia.py`. No editar a mano.", "", "## Modelos", ""]
L += [f"- {m['modelo']} – versión {m['version']} – `{m['archivo']}` – sha256 `{m['sha256'][:16]}…`" for m in cat.resumen()["modelos"]]
L += ["", f"Sistema de referencia de la estructura intermedia: **EPSG:{cat.srid}** (MAGNA-SIRGAS / Origen-Nacional).", "",
      "## Estructura intermedia oficial (script 1) y dominios (scripts 2 y 4)", ""]
for t, cols in cat.intermedia["tablas"].items():
    L += [f"### {t}", "", "| Columna | Tipo oficial | Obligatoria | Dominio |", "|---|---|---|---|"]
    for c in cols:
        d = idx.get((t, c["nombre"]))
        L.append(f"| {c['nombre']} | `{c['tipo_sql']}` | {'Sí' if c['obligatorio'] else 'No'} | {d.nombre if d else ''} |")
    L.append("")
L += ["## Dominios usados por la estructura intermedia (valores hoja válidos = ilicode)", ""]
for n in sorted({d.nombre for d in idx.values()}):
    L += [f"### {n}", ""] + [f"- `{c}` – {s}" for c, s in cat.dominios[n].hojas()] + [""]
L += ["## Asociaciones del modelo extendido", ""]
L += [f"- **{a['nombre']}**: " + "; ".join(f"{r['rol']} {{{r['cardinalidad']}}} {r['clase']}" for r in a["roles"])
      for a in cat.asociaciones if a["nombre"].startswith("pot_")]
L += ["", "## Tablas del esquema LADM_COL-POT que espera el ETL oficial (script 4)", "", ", ".join(f"`{t}`" for t in cat.tablas_etl)]
(BASE / "docs" / "REFERENCIA_TECNICA_MODELO.md").write_text("\n".join(L), encoding="utf-8")
cat.exportar_json(BASE / "docs" / "catalogo_modelo_LADM_COL_POT.json")
print("Referencia regenerada:", len(L), "líneas")
