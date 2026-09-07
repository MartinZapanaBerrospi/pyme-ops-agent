---
skill_id: "SOP-SKILL-001"
skill_name: "audit_pyme_cashflow"
version: "1.0.0"
author: "System Architect Agent"
sdlc_phase: "Fase 3: Diseño del Sistema"
status: "Aprobado"
date: 2026-09-07
entorno_ejecucion: "Python 3.10+ / CLI local / Sin APIs externas"
tags:
  - sop
  - skill
  - auditoria
  - cashflow
  - pyme
---

# 🛠️ SOP del Skill: `audit_pyme_cashflow`

> **Skill ID:** SOP-SKILL-001  
> **Versión:** 1.0.0  
> **Entorno de Ejecución:** Python 3.10+, librería estándar únicamente, ejecución local offline.  
> **Módulo Principal:** `tools/audit_engine.py`

---

## 1. Metadata del Skill

| Atributo | Valor |
| :--- | :--- |
| **Nombre del Skill** | `audit_pyme_cashflow` |
| **Versión** | 1.0.0 |
| **Punto de Entrada** | `python tools/audit_engine.py [argumentos]` |
| **Entorno Mínimo** | Python 3.10+ |
| **Dependencias Externas** | Ninguna (solo librería estándar) |
| **Compatibilidad de Sistema** | Windows 10+, macOS 12+, Ubuntu 20.04+ |
| **Idempotencia** | ✅ Garantizada — mismo input → mismo output |
| **Latencia Máxima** | < 2.0 segundos para lotes ≤ 10,000 registros |

---

## 2. Trigger / Condiciones de Invocación

El agente orquestador **DEBE** invocar el skill `audit_pyme_cashflow` bajo las siguientes condiciones:

| # | Condición de Disparo | Tipo |
| :---: | :--- | :--- |
| 1 | El operador de caja indica que se ha cerrado la jornada y existe un archivo de transacciones del día pendiente de cuadre. | **Manual / Explícito** |
| 2 | Se detecta que el archivo `data/input/transactions_YYYY-MM-DD.csv` o `.json` ha sido creado o modificado en las últimas 24 horas. | **Automático / Por Evento de Archivo** |
| 3 | El administrador solicita una re-auditoría de un día anterior especificando una fecha explícita. | **Manual / Retroactivo** |
| 4 | El sistema detecta que el archivo `reports/AUDIT_YYYY-MM-DD.md` aún no existe para la fecha del día en curso luego de las 21:00 hrs. | **Automático / Por Ausencia de Artefacto** |

### 2.1 Condiciones de NO-Invocación (Guardia)
El agente **NO DEBE** invocar este skill si:
- El archivo `--input` especificado no existe en disco.
- El archivo `--schema` no es un JSON Schema válido (falla de parseo).
- El archivo de entrada tiene 0 registros procesables (dataset completamente vacío post-validación).

---

## 3. Contrato de Interfaz CLI — Parámetros

```bash
python tools/audit_engine.py \
  --input   <ruta_al_archivo_de_transacciones> \
  --schema  <ruta_al_json_schema_de_validacion> \
  --output  <ruta_destino_del_reporte_markdown> \
  --tolerance <porcentaje_de_tolerancia_de_descuadre>
```

### 3.1 Especificación Detallada de Argumentos

| Argumento | Tipo | Obligatorio | Descripción | Ejemplo |
| :--- | :--- | :---: | :--- | :--- |
| `--input` | `str` / `Path` | ✅ Sí | Ruta absoluta o relativa al archivo de transacciones del día a auditar (`.csv` o `.json`). | `data/input/transactions_2026-09-07.csv` |
| `--schema` | `str` / `Path` | ✅ Sí | Ruta al esquema JSON Schema de validación formal. Si se omite se usa el valor por defecto. | `data/schemas/transactions_schema.json` |
| `--output` | `str` / `Path` | ✅ Sí | Ruta y nombre del archivo Markdown del reporte ejecutivo de salida. | `reports/AUDIT_2026-09-07.md` |
| `--tolerance` | `float` | ❌ No | Porcentaje (0–100) de descuadre tolerable antes de emitir alerta `CRITICAL_MISMATCH`. **Default: `5.0`** | `--tolerance 5.0` |
| `--declared` | `float` | ❌ No | Monto total declarado manualmente en el arqueo físico de caja. Si se proporciona, el motor evalúa la discrepancia frente al balance calculado. | `--declared 4850.00` |
| `--date` | `str` | ❌ No | Fecha de auditoría en formato `YYYY-MM-DD`. Si no se especifica, usa la fecha actual del sistema. | `--date 2026-09-07` |

### 3.2 Ejemplo de Invocación Completa
```bash
python tools/audit_engine.py \
  --input data/input/transactions_2026-09-07.csv \
  --schema data/schemas/transactions_schema.json \
  --output reports/AUDIT_2026-09-07.md \
  --tolerance 5.0 \
  --declared 4850.00 \
  --date 2026-09-07
```

---

## 4. Estándar de Salida — Plantilla del Reporte Ejecutivo

El motor **DEBE** generar un archivo Markdown con la siguiente estructura exacta:

```markdown
---
title: "Dictamen de Auditoría Operativa — YYYY-MM-DD"
fecha_auditoria: YYYY-MM-DD
proyecto: "PYME Ops Agent"
skill: "audit_pyme_cashflow"
version_skill: "1.0.0"
estado_auditoria: "BALANCE_OK | CRITICAL_MISMATCH"
tags:
  - auditoria
  - cashflow
  - reporte
---

# 📊 Dictamen de Auditoría de Caja — YYYY-MM-DD

> **Estado:** 🟩 BALANCE_OK | 🟥 CRITICAL_MISMATCH  
> **Fecha de Procesamiento:** YYYY-MM-DD HH:MM:SS  
> **Archivos Analizados:** `transactions_YYYY-MM-DD.csv`  
> **Tolerancia de Descuadre Configurada:** 5.0%

---

## 1. Resumen Ejecutivo (KPIs de Caja)

| Indicador                    | Valor          |
| :--------------------------- | :------------- |
| Total de Transacciones       | N              |
| Transacciones Válidas        | N              |
| Transacciones Rechazadas (DLQ)| N             |
| Duplicados Detectados         | N              |
| **Total Ingresos**           | **S/ X,XXX.XX**|
| **Total Egresos**            | **S/ X,XXX.XX**|
| **Balance Neto Calculado**   | **S/ X,XXX.XX**|
| Monto Declarado (Arqueo)     | S/ X,XXX.XX    |
| **Discrepancia Absoluta**    | **S/ X.XX**    |
| **Porcentaje de Descuadre**  | **X.XX%**      |

---

## 2. Desglose por Método de Pago

| Método de Pago | Total Ingresos | Total Egresos | Neto       |
| :------------- | :------------- | :------------ | :--------- |
| Efectivo       | S/ X,XXX.XX    | S/ XXX.XX     | S/ X,XXX.XX|
| POS (Tarjeta)  | S/ X,XXX.XX    | S/ 0.00       | S/ X,XXX.XX|
| Yape           | S/ XXX.XX      | S/ 0.00       | S/ XXX.XX  |
| Plin           | S/ XXX.XX      | S/ 0.00       | S/ XXX.XX  |
| **TOTAL**      | **S/ X,XXX.XX**| **S/ XXX.XX** |**S/ X,XXX.XX**|

---

## 3. Alertas y Anomalías Detectadas

> [!WARNING]
> **CRITICAL_MISMATCH**: La discrepancia entre el balance calculado y el monto declarado supera el umbral del 5.0%.

| ID Alerta | Tipo           | Descripción                          | Severidad  |
| :-------- | :------------- | :----------------------------------- | :--------- |
| ALT-001   | DUPLICATE      | TRX-045 y TRX-046 — mismo monto y referencia en 47s | MEDIUM |
| ALT-002   | MISMATCH       | Descuadre neto: S/ -45.50 (2.10%)   | CRITICAL   |

---

## 4. Registros Rechazados (Dead Letter Queue)

> [!CAUTION]
> **N registros** no pasaron la validación de esquema y fueron enviados a cuarentena en `data/dlq/`.

| DLQ ID       | Campo Inválido | Motivo de Rechazo          |
| :----------- | :------------- | :------------------------- |
| DLQ-001      | `monto`        | Valor no numérico: "veinte"|
| DLQ-002      | `timestamp`    | Formato no conforme        |

---

*Dictamen generado automáticamente por `audit_pyme_cashflow v1.0.0` — PYME Ops Agent SDLC*
```

### 4.1 Reglas de Compatibilidad con Obsidian
- El frontmatter YAML **es obligatorio** y debe ser el primer elemento del archivo.
- Los tags `auditoria`, `cashflow` y `reporte` deben incluirse siempre para garantizar indexación en el grafo de Obsidian.
- Los callouts (`> [!WARNING]`, `> [!CAUTION]`) utilizan la sintaxis nativa de Obsidian y GitHub Flavored Markdown.
- Las tablas deben usar el formato de tuberías (`|`) con cabecera separada por `---`.
- Todos los montos monetarios deben incluir el prefijo de moneda (ejemplo: `S/` para Soles peruanos) con separador de miles y 2 decimales fijos.

---

## 5. Códigos de Salida del Proceso CLI

| Código | Nombre | Condición |
| :---: | :--- | :--- |
| `0` | `SUCCESS_BALANCE_OK` | Auditoría completada sin descuadres críticos. |
| `1` | `SUCCESS_CRITICAL_MISMATCH` | Auditoría completada pero con descuadre superior al umbral. Reporte generado con alertas. |
| `2` | `ERROR_INVALID_INPUT` | Archivo de entrada no encontrado o no legible. |
| `3` | `ERROR_SCHEMA_LOAD_FAILURE` | Esquema JSON inválido o no encontrado. |
| `4` | `ERROR_EMPTY_DATASET` | Cero registros válidos procesados tras la validación. |
| `99` | `ERROR_UNEXPECTED` | Error de sistema no controlado. Revisar log de traza. |

---

## Navegación del Proyecto (Obsidian Graph)

| Nodo | Enlace |
| :--- | :--- |
| Inicio del Proyecto | [[README]] |
| Fase 1: Planificación | [[01_fase_planificacion]] |
| Fase 2: Análisis | [[02_fase_analisis_requisitos]] |
| Fase 3: Diseño | [[03_fase_diseno_arquitectura]] |
| Fase 4: Implementación | [[04_fase_implementacion]] |
| Rol: Business Analyst | [[01_business_analyst]] |
| Rol: System Architect | [[02_system_architect]] |
| Rol: Software Engineer | [[03_software_engineer]] |
| Rol: QA Engineer | [[04_qa_engineer]] |
