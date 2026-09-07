---
title: "SOP-002: Procedimiento Operativo Estándar de Mantenimiento y Operaciones SRE"
document_type: "Standard Operating Procedure (SOP) & Runbook"
sop_id: "SOP-MNT-002"
version: "1.0.0"
author: "SRE (Site Reliability Engineer) & Lead de Operaciones"
status: "Aprobado"
date: 2026-09-07
tags:
  - sop
  - runbook
  - mantenimiento
  - sre
  - operaciones
---

# 📖 SOP-002: Runbook Operativo de Mantenimiento y Confiabilidad (SRE)

> **Identificador:** SOP-MNT-002  
> **Versión Vigente:** 1.0.0  
> **Área Responsable:** SRE & Lead de Operaciones (`[[02_system_architect]]` / DevOps Lead)  
> **Objetivo:** Establecer los protocolos sistemáticos para la atención de incidentes en el Dead Letter Queue (DLQ), la gobernanza del versionado semántico y la política de retención y resguardo de artefactos contables.

---

## 1. Protocolo de Gestión de Incidencias en Dead Letter Queue (DLQ)

Cuando el motor de salud (`tools/maintenance_healthcheck.py`) o el informe diario detectan registros en el DLQ (`reports/dlq_anomalias.json`), se debe ejecutar el siguiente flujo operativo:

```text
┌────────────────────────┐     ┌────────────────────────┐     ┌────────────────────────┐
│  1. Detección en DLQ   │ ──► │  2. Análisis de Causa  │ ──► │ 3. Corrección en Origen│
│ reports/dlq_anomalias  │     │   Campo incriminado    │     │  Base POS o Libro Caja │
└────────────────────────┘     └────────────────────────┘     └───────────┬────────────┘
                                                                          │
                               ┌────────────────────────┐                 │
                               │  5. Regeneración Acta  │ ◄───────────────┘
                               │  AuditResult Conforme  │  4. Reprocesamiento
                               └────────────────────────┘
```

### Paso a Paso de Remediación:
1. **Inspección del Envelope DLQ:**
   Abrir `reports/dlq_anomalias.json` y clasificar la causa de rechazo:
   - `campo_incriminado: monto` con valor no numérico o `<= 0`.
   - `campo_incriminado: timestamp` con fecha no ISO 8601.
   - `campo_incriminado: tipo` o `metodo_pago` con valor fuera del catálogo formal.
   - `campo obligatorio ausente`: Omisión en el punto de captura.
2. **Subsanación en el Sistema Fuente (POS o ERP de la PYME):**
   - **Prohibido alterar directamente los logs históricos sin trazabilidad.**
   - La corrección debe realizarse en el sistema de facturación o registro de ventas de origen para emitir la transacción rectificada con su respectivo identificador de compensación o referencia auditada.
3. **Reprocesamiento Controlado:**
   Generar un dataset saneado y ejecutar nuevamente el motor de auditoría:
   ```bash
   python tools/audit_engine.py --input data/ventas_diarias.csv --schema data/schemas/transactions_schema.json --output reports/cierre_diario_actual.md --tolerance 5.0
   ```
4. **Validación de Cierre:**
   Ejecutar el healthcheck para verificar que la tasa de rechazo DLQ retorne a 0.0%:
   ```bash
   python tools/maintenance_healthcheck.py
   ```

---

## 2. Política de Versionado Semántico (SemVer 2.0.0)

Cualquier cambio evolutivo en el esquema de datos (`transactions_schema.json`) o en el motor (`audit_engine.py`) debe cumplir estrictamente las siguientes reglas de versionado:

| Tipo de Cambio | Formato SemVer | Criterio de Aplicación | Ejemplo Práctico |
| :--- | :---: | :--- | :--- |
| **MAJOR (Mayor)** | `X.0.0` | **Cambios incompatibles hacia atrás (Breaking Changes).** <br>• Eliminación de campos obligatorios en el schema.<br>• Modificación de tipos o contratos existentes.<br>• Modificación de argumentos CLI que rompa la compatibilidad con clientes existentes. | Migración a schema v2 con campos obligatorios para impuestos fiscales o moneda extranjera. |
| **MINOR (Menor)** | `1.X.0` | **Nuevas funcionalidades compatibles hacia atrás.** <br>• Nuevos campos opcionales en el schema (ej. `vendedor_id`, `descuento`).<br>• Incorporación de nuevos canales de pago en el enum sin alterar los actuales (ej. `apple_pay`).<br>• Nuevas herramientas expuestas en el servidor MCP. | Integración de nuevo método de pago `billetera_bim` en el enum sin alterar transacciones existentes. |
| **PATCH (Parche)** | `1.0.X` | **Corrección de errores y optimizaciones sin alterar interfaces.** <br>• Refactorizaciones internas de rendimiento.<br>• Corrección de textos, mensajes de error o visualización en Markdown.<br>• Actualización de pruebas unitarias o documentación. | Optimización en el algoritmo de búsqueda de duplicados O(n²) para mejorar latencia. |

---

## 3. Política de Rotación, Resguardo y Retención de Artefactos

Para garantizar la durabilidad de los registros contables sin degradar el rendimiento del repositorio ni saturar el espacio en disco de las estaciones PYME:

### 3.1 Ciclo de Archivo Mensual
Al finalizar cada mes calendario (día 1 del mes siguiente):
1. Crear el directorio de consolidación histórica: `reports/archive/YYYY-MM/`.
2. Mover todos los dictámenes diarios generados durante el mes:
   ```bash
   mkdir -p reports/archive/2026-09/
   mv reports/AUDIT_2026-09-*.md reports/archive/2026-09/
   ```
3. Generar un resumen mensual de auditoría consolidado (`reports/archive/2026-09/RESUMEN_MENSUAL.md`).

### 3.2 Política de Retención y Purga de Logs
- **Dictámenes de Auditoría (`.md`):** Conservación obligatoria de **al menos 12 meses** en disco local o bóveda Obsidian, y respaldo permanente en el repositorio Git remoto.
- **Dead Letter Queue (`dlq_anomalias.json`):** Retención máxima de **90 días**. Las anomalías resueltas mayores a 90 días deben archivarse en formato comprimido `dlq_archive_YYYY.json.gz` y purgarse del archivo caliente para mantener el archivo principal liviano.
- **Inmutabilidad:** Los archivos en `data/input/` o copias de trabajo no deben sobrescribirse; cada lote auditado debe conservar su nombre con marca temporal de la jornada.

---

## Navegación del Proyecto (Obsidian Graph)

| Nodo | Enlace |
| :--- | :--- |
| Inicio del Proyecto | [[README]] |
| Documento de Cierre SDLC | [[07_fase_mantenimiento]] |
| Diagnóstico de Salud del Sistema | [[system_health_status]] |
| Fase de Despliegue | [[06_fase_despliegue]] |
| Fase de Pruebas | [[05_fase_pruebas]] |
| SOP de Auditoría de Caja | [[sop_auditoria_caja]] |
| Roles del Equipo | [[01_business_analyst]] · [[02_system_architect]] · [[03_software_engineer]] · [[04_qa_engineer]] |
