# Toolkit LADM_COL-POT – Automatización y estructuración cartográfica

Convierte los insumos cartográficos desorganizados de un municipio en la **estructura de datos intermedia oficial**
del modelo **LADM_COL_v_2_0_0_Ext_POT (versión 2.0)**, adoptado por la Resolución 0058 de 2025 del MVCT,
con inventario, homologación, validación, reportes y carpeta de entrega trazable.

> **Qué hace y qué no hace.** Sigue la ruta de la *Guía para la migración de datos al modelo LADM_COL-POT* (MVCT):
> diagnóstico → depuración → estructura intermedia → ETL/XTF. El toolkit automatiza las tres primeras fases y
> prepara la cuarta. La generación del **XTF** y su validación con **ilivalidator** requieren PostgreSQL/PostGIS,
> el ETL oficial y Java (scripts incluidos en `04_BASE_DATOS_LADM_COL_POT/fase4_migracion`). Mientras no se
> ejecuten, los reportes marcan la validación INTERLIS como **NO EJECUTADA**: el paquete nunca declara conformidad
> plena sin ese paso.

## Instalación

```bash
python -m pip install -r requirements.txt     # Python 3.10+
```
En QGIS (Windows) puede usar la consola *OSGeo4W Shell*: `python -m pip install openpyxl pypdf`.

## Uso

```bash
# 1) Primera pasada: inventario, clasificación y todo lo que se pueda homologar con seguridad
python -m ladm_pot.pipeline --insumos <carpeta_insumos> --salida <carpeta_salida> --proyecto proyecto.json

# 2) Revise 08_REPORTES/decisiones_pendientes.json, complételo y guárdelo como decisiones.json
# 3) Segunda pasada con sus decisiones
python -m ladm_pot.pipeline --insumos <carpeta_insumos> --salida <carpeta_salida> --proyecto proyecto.json --decisiones decisiones.json

# Opcional (fase 4 hecha): validar el XTF con ilivalidator
python -m ladm_pot.pipeline ... --xtf entrega.xtf --ilivalidator /ruta/ilivalidator.jar
```

`proyecto.json` (ver `config/proyecto_ejemplo.json`): datos del municipio (DIVIPOLA, NIT) y de las fuentes
administrativa y espacial. Los valores de dominio se escriben con el código oficial (*ilicode*).

## Reglas de funcionamiento

| Tema | Regla |
|---|---|
| Modelo | Clases, atributos, dominios y estructura intermedia se leen de `modelo_oficial/` (archivos .ili y SQL oficiales). Nada está escrito a mano. Si se publica una versión posterior, reemplace esa carpeta. |
| Originales | Se copian a `01_INSUMOS_ORIGINALES`; todo el procesamiento usa copias de trabajo. |
| Clasificación de capas | Heurística (nombre + campos + valores que coinciden con dominios + tipo de geometría). Solo carga automáticamente con confianza **ALTA**; lo demás queda pendiente con sugerencia. Capas sin correspondencia se conservan, nunca se descartan. |
| Capas equivalentes | Si dos capas del mismo destino se superponen > 50 %, **no se fusionan**: quedan pendientes hasta que el usuario elija. Capas complementarias (amenazas por fenómeno, sistemas generales) se anexan. |
| CRS | Nunca se asume. Se usa el declarado por el archivo, el fijado por especificación (KML = WGS84) o el indicado por el usuario. Sin CRS → CRÍTICO y la capa no se carga. Toda reproyección se documenta. Destino: EPSG:9377. |
| Dominios | Solo coincidencia **exacta** normalizada (código, último segmento único o dispName oficial) o decisión del usuario. Valores de nodos no hoja (p. ej. `Renovación urbana`) quedan pendientes con sus hijos sugeridos. |
| Geometrías | `make_valid` sobre la copia, filtrado al tipo destino, Z=0 (la estructura intermedia es 3D), separación de multipartes cuando el destino es simple. Todo se registra. |
| Identificadores | Se conservan si vienen únicos; si no, se generan (`<DANE>_<tabla>_<n>`) y la tabla `zz_trazabilidad_origen` liga cada registro con archivo y fid de origen. |
| Cumplimiento | Porcentaje sobre reglas **evaluadas**; las no ejecutadas o sin datos se reportan aparte. |

## Validaciones implementadas

* **Oficiales (repositorio del modelo):** estructura y NOT NULL (script 1); dominios y DRR (script 2);
  topológicas T1, T5, T6, T8, T10, T12, T13, T15, T16, T17, T18; consistencia lógica CL1–CL4, CL6–CL8, CL16,
  CL27, CL29, CL30 (las de obligatoriedad quedan cubiertas por NOT NULL); temáticas TM1–TM4.
* **Modelo ILI:** asociaciones pot_clasificacionsuelo_zonificacionsuelo y pot_zonificacionsuelo_centropoblado.
* **Toolkit (control de calidad adicional, no oficial):** validez OGC, duplicados, objetos fuera del límite,
  cobertura del municipio por la clasificación del suelo, cobertura del suelo rural por la zonificación,
  completitud de fuentes.
* **INTERLIS:** ilivalidator sobre el XTF (cuando se suministra).

## Estructura del código

```
ladm_pot/modelo.py        Parser INTERLIS + estructura intermedia + reglas de dominio (desde archivos oficiales)
ladm_pot/inventario.py    Recepción, ZIP/KMZ, inventario (vector, tabla, ráster, documento), calidad geométrica
ladm_pot/homologacion.py  Clasificación de capas, CRS, geometrías, homologación de campos y dominios
ladm_pot/validacion.py    Motor de validación (estructural, semántica, espacial, relacional, documental, INTERLIS)
ladm_pot/salida.py        GeoPackage intermedio, scripts fase 4, Excel, informe MD/HTML, vistas, manifiesto, ZIP
ladm_pot/pipeline.py      Orquestador por lotes (CLI)
config/                   Reglas heurísticas editables y proyecto de ejemplo
modelo_oficial/           Archivos oficiales del modelo (ver PROCEDENCIA.md)
tests/                    Generador de municipio sintético + decisiones simuladas + prueba integral
docs/                     Referencia técnica y ejemplo de procesamiento
```

## Prueba integral

```bash
bash tests/prueba_integral.sh
```
Genera un municipio **sintético** (no real) con 10 formatos, 4 sistemas de referencia, capas equivalentes,
geometría inválida y valores no homologables; ejecuta las dos pasadas y verifica la salida.
