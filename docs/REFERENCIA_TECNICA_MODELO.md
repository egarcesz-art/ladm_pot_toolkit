# Referencia técnica – catálogo generado desde los archivos oficiales

Generado automáticamente desde `modelo_oficial/` con `python docs/generar_referencia.py`. No editar a mano.

## Modelos

- ISO19107_PLANAS_V3_1 – versión 2016-03-07 – `ISO19107_PLANAS_V3_1.ili` – sha256 `6dc4be70acf31a1f…`
- LADM_COL_v_2_0_0_Ext_POT – versión 2.0.0 – `LADM_COL_v_2_0_0_Ext_POT.ili` – sha256 `6b0a95671b1516af…`
- LADM_COL_v_4_0_1_Nucleo – versión V1.2.0 – `LADM_COL_v_4_0_1_Nucleo.ili` – sha256 `41676304377434b0…`

Sistema de referencia de la estructura intermedia: **EPSG:9377** (MAGNA-SIRGAS / Origen-Nacional).

## Estructura intermedia oficial (script 1) y dominios (scripts 2 y 4)

### area_condicion_amenaza

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| fenomeno | `varchar(255)` | Sí | POT_FenomenoAmenazaTipo |
| categoria_amenaza | `varchar(255)` | No | POT_CategoriaAmenazaTipo |
| priorizacion | `varchar(255)` | No | POT_PriorizacionTipo |
| medida_intervencion | `varchar(255)` | No | POT_MedidaIntervencionTipo |
| detalle_medida_intervencion | `varchar(500)` | No |  |
| detalle_fenomeno | `varchar(500)` | No |  |
| nombre | `varchar(255)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(multipolygonz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### area_condicion_riesgo

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| fenomeno | `varchar(255)` | Sí | POT_FenomenoAmenazaTipo |
| priorizacion | `varchar(255)` | No | POT_PriorizacionTipo |
| medida_intervencion | `varchar(255)` | No | POT_MedidaIntervencionTipo |
| detalle_medida_intervencion | `varchar(500)` | No |  |
| detalle_fenomeno | `varchar(500)` | No |  |
| nombre | `varchar(255)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(multipolygonz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### areas_actividad

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| uso_principal | `varchar(255)` | Sí | POT_AreaActividadTipo |
| detalle_uso_principal | `varchar(255)` | Sí |  |
| uso_compatible_complementario | `varchar(500)` | Sí |  |
| uso_condicionado_restringido | `varchar(500)` | Sí |  |
| uso_prohibido | `varchar(500)` | Sí |  |
| nombre | `varchar(255)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(multipolygonz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### centro_poblado_rural

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| nombre | `varchar(255)` | Sí |  |
| codigo | `varchar(8)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(multipolygonz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### clasificacion_suelo

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| tipo_clasificacion_suelo | `varchar(255)` | Sí | POT_ClasificacionSueloTipo |
| nombre | `varchar(255)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(multipolygonz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### sistemas_generales_poligono

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| tipo_sistema_general | `varchar(255)` | Sí | POT_SistemasGeneralesTipo |
| detalle_sistema_general | `varchar(255)` | Sí |  |
| nivel | `varchar(255)` | Sí | POT_SistemasGeneralesNivelTipo |
| estado | `varchar(255)` | Sí | POT_SistemasGeneralesEstadoTipo |
| nombre | `varchar(255)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(multipolygonz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### sistemas_generales_linea

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| tipo_sistema_general | `varchar(255)` | Sí | POT_SistemasGeneralesTipo |
| detalle_sistema_general | `varchar(255)` | Sí |  |
| nivel | `varchar(255)` | Sí | POT_SistemasGeneralesNivelTipo |
| estado | `varchar(255)` | Sí | POT_SistemasGeneralesEstadoTipo |
| nombre | `varchar(255)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(linestringz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### sistemas_generales_punto

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| tipo_sistema_general | `varchar(255)` | Sí | POT_SistemasGeneralesTipo |
| detalle_sistema_general | `varchar(255)` | Sí |  |
| nivel | `varchar(255)` | Sí | POT_SistemasGeneralesNivelTipo |
| estado | `varchar(255)` | Sí | POT_SistemasGeneralesEstadoTipo |
| nombre | `varchar(255)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(pointz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### suelo_proteccion_urbano

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| uso_principal | `varchar(255)` | Sí | POT_SueloProteccionUrbanoTipo |
| detalle_uso_principal | `varchar(255)` | Sí |  |
| uso_compatible_complementario | `varchar(500)` | Sí |  |
| uso_condicionado_restringido | `varchar(500)` | Sí |  |
| uso_prohibido | `varchar(500)` | Sí |  |
| nombre | `varchar(255)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(multipolygonz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### tratamiento_urbanistico

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| tipo_tratamiento_urbanistico | `varchar(255)` | Sí | POT_TratamientoUrbanisticoTipo |
| nombre | `varchar(255)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(multipolygonz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### zonificacion_amenaza

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| fenomeno | `varchar(255)` | Sí | POT_FenomenoAmenazaTipo |
| categoria_amenaza | `varchar(50)` | No | POT_CategoriaAmenazaTipo |
| descripcion | `varchar(255)` | No |  |
| detalle_fenomeno | `varchar(500)` | No |  |
| nombre | `varchar(255)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(multipolygonz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### zonificacion_suelo_rural

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| identificador | `varchar(50)` | No |  |
| uso_principal | `varchar(255)` | Sí | POT_UsoSueloRuralTipo |
| tipo_categoria_rural | `varchar(255)` | No | POT_CategoriaRuralTipo |
| detalle_uso_principal | `varchar(255)` | Sí |  |
| uso_compatible_complementario | `varchar(500)` | Sí |  |
| uso_condicionado_restringido | `varchar(500)` | Sí |  |
| uso_prohibido | `varchar(500)` | Sí |  |
| nombre | `varchar(255)` | No |  |
| descripcion_derecho | `varchar(255)` | No |  |
| descripcion_restriccion | `varchar(255)` | No |  |
| descripcion_responsabilidad | `varchar(255)` | No |  |
| area_m2 | `numeric(14,1)` | No |  |
| geometria | `public.geometry(multipolygonz, 9377)` | No |  |
| fuente_administrativa_tipo | `varchar(255)` | Sí | POT_FuenteAdministrativaTipo |
| fuente_administrativa_tipo_pot | `varchar(255)` | No | POT_PlanOrdenamientoTerritorialTipo |
| fuente_administrativa_estado_disponibilidad | `varchar(255)` | Sí | COL_EstadoDisponibilidadTipo |
| fuente_administrativa_fecha_documento | `date` | No |  |
| fuente_administrativa_numero_fuente | `varchar(150)` | No |  |
| fuente_administrativa_tipo_revision | `varchar(255)` | No | POT_RevisionTipo |
| fuente_espacial_tipo | `varchar(255)` | No | COL_FuenteEspacialTipo |
| fuente_espacial_estado_disponibilidad | `varchar(255)` | No | COL_EstadoDisponibilidadTipo |
| fuente_espacial_metadato | `text` | No |  |
| fuente_espacial_escala | `numeric(12, 3)` | No |  |
| fuente_espacial_fecha_publicacion | `date` | No |  |
| fuente_espacial_responsable | `varchar(500)` | No |  |
| fuente_espacial_nombre | `varchar(255)` | No |  |
| fuente_espacial_fecha_documento | `date` | No |  |

### municipio

| Columna | Tipo oficial | Obligatoria | Dominio |
|---|---|---|---|
| codigo_departamento | `varchar(2)` | Sí |  |
| codigo_municipio | `varchar(3)` | Sí |  |
| nombre_municipio | `varchar(255)` | Sí |  |
| tipo_interesado | `varchar(255)` | Sí | COL_InteresadoTipo |
| tipo_documento | `varchar(255)` | No | COL_DocumentoTipo |
| numero_documento | `varchar(255)` | No |  |

## Dominios usados por la estructura intermedia (valores hoja válidos = ilicode)

### COL_DocumentoTipo

- `Cedula_Ciudadania` – Cédula de ciudadanía
- `Cedula_Extranjeria` – Cédula de extranjería
- `NIT` – NIT
- `Pasaporte` – Pasaporte
- `Registro_Civil` – Registro civil
- `Tarjeta_Identidad` – Tarjeta de identidad

### COL_EstadoDisponibilidadTipo

- `Convertido` – Convertido
- `Desconocido` – Desconocido
- `Disponible` – Disponible

### COL_FuenteEspacialTipo

- `Croquis_Campo` – Croquis de campo
- `Datos_Crudos` – Datos crudos (GPS, Estación total, LiDAR, etc.)
- `Ortofoto` – Ortofoto
- `Informe_Tecnico` – Informe técnico
- `Registro_Fotografico` – Registro fotográfico

### COL_InteresadoTipo

- `Persona_Natural` – Persona Natural
- `Persona_Juridica` – Persona Jurídica

### POT_AreaActividadTipo

- `Residencial` – Residencial
- `Comercial` – Comercial
- `Servicios` – Servicios
- `Industrial` – Industrial
- `Institucional` – Institucional
- `Dotacional` – Dotacional
- `Mixto` – Mixto
- `Otro` – Otro

### POT_CategoriaAmenazaTipo

- `Alta` – Categoría alta
- `Media` – Categoría media
- `Baja` – Categoría baja

### POT_CategoriaRuralTipo

- `Suelo_Rural_Productivo.Agropecuario` – (Suelo rural productivo) Agropecuario
- `Suelo_Rural_Productivo.Forestal` – (Suelo rural productivo) Forestal
- `Suelo_Rural_Productivo.Mineria_Hidrocarburos` – (Suelo rural productivo) Minería e hidrocarburos
- `Desarrollo_Restringido.Suburbano` – (Desarrollo restringido) Suburbano
- `Desarrollo_Restringido.Corredor_Vial_Suburbano` – (Desarrollo restringido) Corredor vial suburbano
- `Desarrollo_Restringido.Centro_Poblado_Rural` – (Desarrollo restringido) Centro poblado en la zona rural
- `Desarrollo_Restringido.Vivienda_Campestre` – (Desarrollo restringido) Vivienda campestre
- `Desarrollo_Restringido.Equipamento` – (Desarrollo restringido) Equipamiento
- `Proteccion_Suelo_Rural.Conservacion_Proteccion_Ambiental.Areas_SINAP` – (Protección suelo rural-Conservación y protección ambiental) Áreas SINAP
- `Proteccion_Suelo_Rural.Conservacion_Proteccion_Ambiental.Areas_Reserva_Forestal` – (Protección suelo rural-Conservación y protección ambiental) Áreas de reserva forestal
- `Proteccion_Suelo_Rural.Conservacion_Proteccion_Ambiental.Areas_Manejo_Especial` – (Protección suelo rural-Conservación y protección ambiental) Áreas de manejo especial
- `Proteccion_Suelo_Rural.Conservacion_Proteccion_Ambiental.Areas_Importancia_Ecosistemica` – (Protección suelo rural-Conservación y protección ambiental) Áreas de especial importancia ecosistémica
- `Proteccion_Suelo_Rural.Produccion_Agropecuaria_Explotacion_RRNN` – (Protección Suelo Rural) Producción agrícola, ganadera y de explotación de recursos naturales
- `Proteccion_Suelo_Rural.Sistema_Servicios_Publicos` – (Protección suelo rural) Sistema de servicios públicos domiciliarios
- `Proteccion_Suelo_Rural.Amenaza_Y_Riesgo_No_Mitigable` – (Protección suelo rural) Amenaza y riesgo no mitigable
- `Proteccion_Suelo_Rural.Patrimonio_Cultural` – (Protección suelo rural) Patrimonio cultural

### POT_ClasificacionSueloTipo

- `Urbano` – Urbano
- `Rural` – Rural
- `Expansion_Urbana` – Expansión urbana

### POT_FenomenoAmenazaTipo

- `Movimientos_En_Masa` – Movimientos en masa
- `Avenida_Torrencial` – Avenida torrencial
- `Inundacion` – Inundación
- `Incendios_Forestales` – Incendios forestales
- `Tsunami` – Tsunami
- `Volcanico` – Volcánico
- `Huracanes` – Huracanes
- `Sismica` – Sísmica
- `Erosion_Costera` – Erosión costera
- `Vendavales` – Vendavales
- `Tecnologico` – Tecnológico
- `Otro` – Otro
- `Sin_Determinar` – Sin determinar

### POT_FuenteAdministrativaTipo

- `Documento_Publico.Acuerdo` – Acuerdo
- `Documento_Publico.Decreto` – Decreto
- `Documento_Publico.Concertacion_Junta_Metropolitana` – Concertacion_Junta_Metropolitana
- `Documento_Publico.Acta_Concertacion` – Acta de concertación
- `Documento_Privado` – Documento privado

### POT_MedidaIntervencionTipo

- `Estudios_Detallados` – Estudios detallados
- `Restriccion_O_Condicionamiento_Uso_Del_Suelo` – Restricción o condicionamiento del uso del suelo
- `Monitoreo_Del_Riesgo` – Monitoreo del riesgo
- `Sistema_De_Alerta_Temprana` – Sistemas de alerta temprana
- `Preparacion_Y_Respuesta` – Preparación y respuesta
- `Estudios_Disenios_Y_Obras` – Estudios, diseños y obras
- `Fortalecimiento_Institucional` – Fortalecimiento institucional
- `Apropiacion_Comunitaria_De_La_Gestion_Del_Riesgo_De_Desastres` – Apropiación comunitaria de la gestión del riesgo de desastres
- `Otro` – Otro

### POT_PlanOrdenamientoTerritorialTipo

- `POT` – Plan de ordenamiento territorial
- `PBOT` – Plan básico de ordenamiento territorial
- `EOT` – Esquema de ordenamiento territorial

### POT_PriorizacionTipo

- `Corto_Plazo` – Corto plazo
- `Mediano_Plazo` – Mediano plazo
- `Largo_Plazo` – Largo plazo

### POT_RevisionTipo

- `Revision_Vencimiento_Largo_Plazo` – Revisión por vencimiento de largo plazo
- `Revision_Vencimiento_Mediano_Plazo` – Revisión por vencimiento de mediano plazo
- `Revision_Vencimiento_Corto_Plazo` – Revisión por vencimiento de corto plazo
- `Modificacion_Excepcional_Norma_Urbanistica` – Modificación excepcional de norma urbanística
- `Revision_Excepcional_Interes_Publico` – Revisión por excepcional interés público

### POT_SistemasGeneralesEstadoTipo

- `Existente` – Estado existente
- `Proyectado` – Estado proyectado

### POT_SistemasGeneralesNivelTipo

- `Nacional` – Nivel nacional
- `Departamental` – Nivel departamental
- `Regional` – Nivel regional
- `Municipal` – Nivel municipal
- `Distrital` – Nivel distrital
- `Local` – Nivel local
- `Barrial` – Nivel barrial
- `Zonal` – Nivel zonal
- `Metropolitano` – Nivel metropolitano

### POT_SistemasGeneralesTipo

- `Equipamientos.Educacion` – (Equipamientos) Educación
- `Equipamientos.Cultura` – (Equipamientos) Cultura
- `Equipamientos.Salud` – (Equipamientos) Salud
- `Equipamientos.Bienestar_Social` – (Equipamientos) Bienestar social
- `Equipamientos.Culto` – (Equipamientos) Culto
- `Equipamientos.Deportivo_Recreativo` – (Equipamientos) Deportivo recreativo
- `Equipamientos.Seguridad_Ciudadana` – (Equipamientos) Seguridad ciudadana
- `Equipamientos.Defensa_Justicia` – (Equipamientos) Defensa y justicia
- `Equipamientos.Abastecimiento` – (Equipamientos) Abastecimiento de alimentos y seguridad alimentaria
- `Equipamientos.Recintos_Feriales` – (Equipamientos) Recintos feriales
- `Equipamientos.Cementerios_Servicios_Funerarios` – (Equipamientos) Cementerios y servicios funerarios
- `Equipamientos.Servicios_Administracion_Publica` – (Equipamientos) Servicios de administración pública
- `Equipamientos.Atencion_SPD` – (Equipamientos) Servicios de atención de usuarios de servicio públicos domiciliarios
- `Espacio_Publico.Elemento_Constitutivo` – (Espacio público) Elemento constitutivo de espacio público
- `Espacio_Publico.Elemento_Complementario` – (Espacio público) Elemento complementario de espacio público
- `Servicios_Publicos.Acueducto` – (Servicios públicos) Acueducto
- `Servicios_Publicos.Alcantarillado` – (Servicios públicos) Alcantarillado
- `Servicios_Publicos.Gas` – (Servicios públicos) Gas domiciliario
- `Servicios_Publicos.Energia` – (Servicios públicos) Energía
- `Servicios_Publicos.Telecomunicaciones` – (Servicios públicos) Telecomunicaciones
- `Servicios_Publicos.Disposicion_Final_Residuos.Escombrera` – (Servicios públicos-Disposición final de residuos sólidos) Escombrera
- `Servicios_Publicos.Disposicion_Final_Residuos.Relleno_Sanitario` – (Servicios públicos-Disposición final de residuos sólidos) Relleno Sanitario
- `Vias.Rural.Vias_Primer_Orden` – (Vías-Zona rural) Vías primer orden
- `Vias.Rural.Vias_Segundo_Orden` – (Vías-Zona rural) Vías de segundo orden
- `Vias.Rural.Vias_Tercer_Orden` – (Vías-Zona rural) Vías de tercer orden
- `Vias.Urbano.Principal` – (Vías-Zona urbana) Principal
- `Vias.Urbano.Secundaria` – (Vías-Zona urbana) Secundaria
- `Vias.Urbano.Local` – (Vías-Zona urbana) Local
- `Vias.Urbano.Peatonal` – (Vías-Zona urbana) Peatonal
- `Vias.Urbano.Ciclorruta` – (Vías-Zona urbana) Ciclorruta
- `Infraestructura_Transporte.Terrestre` – (Infraestructura de transporte) Terrestre
- `Infraestructura_Transporte.Aereo` – Aereo
- `Infraestructura_Transporte.Fluvial` – (Infraestructura de transporte) Fluvial
- `Infraestructura_Transporte.Maritimo` – (Infraestructura de transporte) Marítimo

### POT_SueloProteccionUrbanoTipo

- `Ambiental` – Ambiental
- `Infraestructura` – Infraestructura
- `Servicios_Publicos` – Servicios públicos
- `Patrimonio` – Patrimonio
- `Riesgo_No_Mitigable` – Riesgo no mitigable
- `Otro` – Otro

### POT_TratamientoUrbanisticoTipo

- `Desarrollo` – Desarrollo
- `Consolidacion` – Consolidación
- `Renovacion_Urbana.Reactivacion` – (Renovación urbana) Reactivación
- `Renovacion_Urbana.Redesarrollo` – (Renovación urbana) Redesarrollo
- `Renovacion_Urbana.Revitalizacion` – (Renovación urbana) Revitalización
- `Conservacion` – Conservación
- `Mejoramiento_Integral` – Mejoramiento integral

### POT_UsoSueloRuralTipo

- `Agricola` – Agrícola
- `Pecuario` – Pecuario
- `Forestal` – Forestal
- `Acuicultura` – Acuicultura
- `Mineria` – Minería
- `Hidrocarburos` – Hidrocarburos
- `Residencial` – Residencial
- `Dotacional_Institucional` – Dotacional  y/o institucional
- `Industrial` – Industrial
- `Turismo` – Turismo
- `Comercial_Servicios` – Comercial y/o servicios
- `Centro_Poblado` – Centro poblado
- `Conservacion_Proteccion_Ambiental.Preservacion` – (Conservación y protección ambiental) Preservación
- `Conservacion_Proteccion_Ambiental.Conservacion` – (Conservación y protección ambiental) Conservación
- `Conservacion_Proteccion_Ambiental.Restauracion` – (Conservación y protección ambiental) Restauración
- `Conservacion_Proteccion_Ambiental.Conocimiento` – (Conservación y protección ambiental) Conocimiento
- `Conservacion_Proteccion_Ambiental.Uso_Sostenible` – (Conservación y protección ambiental) Uso sostenible
- `Conservacion_Proteccion_Ambiental.Disfrute` – (Conservación y protección ambiental) Disfrute
- `Conservacion_Proteccion_Ambiental.Historico_Cultural` – (Conservación y protección ambiental) Histórico cultural
- `Otro` – Otro

## Asociaciones del modelo extendido

- **pot_clasificacionsuelo_centropoblado**: centro_poblado {0..*} POT_UAB_CentroPobladoRural; clasificacion_suelo {1} POT_UAB_ClasificacionSuelo
- **pot_referencialinea_sistemasgenerales**: sistemasgenerales {1} POT_UE_SistemasGenerales; referencialinea {0..1} POT_ReferenciaLineaSistemasGenerales
- **pot_referenciapunto_sistemasgenerales**: sistemagenerales {1} POT_UE_SistemasGenerales; referenciapunto {0..1} POT_ReferenciaPuntoSistemasGenerales
- **pot_areasactividad_centropoblado**: area_actividad {0..*} POT_UAB_AreasActividad; centro_poblado {0..1} POT_UAB_CentroPobladoRural
- **pot_clasificacionsuelo_zonificacionsuelo**: clasificacion_suelo_rural {1} POT_UAB_ClasificacionSuelo; zonificacion_suelo_rural {0..*} POT_UAB_ZonificacionSueloRural
- **pot_zonificacionsuelo_centropoblado**: pot_desarrollo_restringido {1} POT_UAB_ZonificacionSueloRural; centro_poblado {0..*} POT_UAB_CentroPobladoRural

## Tablas del esquema LADM_COL-POT que espera el ETL oficial (script 4)

`col_documentotipo`, `col_estadodisponibilidadtipo`, `col_fuenteadministrativatipo`, `col_fuenteespacialtipo`, `col_interesadotipo`, `col_relacionsuperficietipo`, `col_rrrfuente`, `col_uebaunit`, `col_uefuente`, `col_unidadadministrativabasicatipo`, `pot_areaactividadtipo`, `pot_categoriaamenazatipo`, `pot_categoriaruraltipo`, `pot_clasificacionsuelotipo`, `pot_derecho`, `pot_fenomenoamenazatipo`, `pot_fuenteadministrativa`, `pot_fuenteespacial`, `pot_medidaintervenciontipo`, `pot_municipio`, `pot_planordenamientoterritorialtipo`, `pot_priorizaciontipo`, `pot_referencialineasistemasgenerales`, `pot_referenciapuntosistemasgenerales`, `pot_responsabilidad`, `pot_restriccion`, `pot_revisiontipo`, `pot_sistemasgeneralesestadotipo`, `pot_sistemasgeneralesniveltipo`, `pot_sistemasgeneralestipo`, `pot_sueloproteccionurbanotipo`, `pot_tratamientourbanisticotipo`, `pot_uab_areacondicionamenaza`, `pot_uab_areacondicionriesgo`, `pot_uab_areasactividad`, `pot_uab_centropobladorural`, `pot_uab_clasificacionsuelo`, `pot_uab_sistemasgenerales`, `pot_uab_sueloproteccionurbano`, `pot_uab_tratamientourbanistico`, `pot_uab_zonificacionamenaza`, `pot_uab_zonificacionsuelorural`, `pot_ue_areacondicionamenaza`, `pot_ue_areacondicionriesgo`, `pot_ue_areasactividad`, `pot_ue_centropobladorural`, `pot_ue_clasificacionsuelo`, `pot_ue_sistemasgenerales`, `pot_ue_sueloproteccionurbano`, `pot_ue_tratamientourbanistico`, `pot_ue_zonificacionamenaza`, `pot_ue_zonificacionsuelorural`, `pot_usocompatiblecomplementariovalor`, `pot_usocondicionadorestringidovalor`, `pot_usoprohibidovalor`, `pot_usosueloruraltipo`, `t_ili2db_basket`