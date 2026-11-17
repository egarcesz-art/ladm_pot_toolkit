# Ejemplo de procesamiento (datos SINTÉTICOS)

Resultado real de `tests/prueba_integral.sh` sobre un municipio ficticio (código 99999).

**Insumos (43 archivos, 15 elementos):** SHP en EPSG:3116, SHP sin `.prj`, GeoPackage en EPSG:9377, GeoJSON y KML
en WGS84, CSV con coordenadas sin CRS, DXF sin CRS, ZIP con un SHP, Excel, GeoTIFF (DEM) y PDF.

**Pasada 1 (sin decisiones):**
- Carga automática solo de lo seguro: áreas de actividad, zonificación rural y amenazas.
- Pendientes: 2 capas sin CRS (tratamientos SHP sin `.prj`, CSV de equipamientos), 2 capas de clasificación del suelo
  equivalentes (100 % de superposición, no se fusionan), 2 clasificaciones con confianza media (centros poblados,
  DXF de vías), valores `Zona verde` y `Ganadería extensiva` sin correspondencia, `fenomeno` obligatorio sin campo.
- Se genera `08_REPORTES/decisiones_pendientes.json` prellenado.

**Pasada 2 (con `tests/decisiones_prueba.json`):** 9 capas cargadas en 9 de 13 tablas. Quedan, como corresponde a
defectos sembrados a propósito:
- `Renovación urbana`: nodo no hoja del dominio → pendiente con sugerencias `Renovacion_Urbana.Reactivacion |
  Redesarrollo | Revitalizacion`.
- T6: superposición de tratamientos; T10: 10 ha de suelo urbano sin área de actividad; G5: suelo rural sin zonificar.
- S2: clasificación del suelo sin descripción de derecho/restricción/responsabilidad.
- I1 (INTERLIS): NO EJECUTADA.
