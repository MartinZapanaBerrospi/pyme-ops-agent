---
title: "Fase 5: Pruebas (Testing) - PYME Ops Agent"
document_type: "Quality Assurance Report & Test Certification"
phase: "05 - Pruebas y Verificación"
project: "PYME Ops Agent"
author: "QA Engineer Agent"
status: "Certificado / 100% Tests Pasados"
date: 2026-09-07
repository: "https://github.com/MartinZapanaBerrospi/pyme-ops-agent"
tags:
  - sdlc
  - testing
  - qa
  - unittest
  - certificacion
---

# Documento de Entregable: Fase 5 — Pruebas (Testing)

> **Proyecto:** PYME Ops Agent  
> **Fase SDLC:** 05 - Pruebas y Verificación  
> **Líder de Fase:** [[04_qa_engineer]]  
> **Artefacto Evaluado:** [[04_fase_implementacion]] (`tools/audit_engine.py`)  
> **Evidencia Operativa:** [[cierre_diario_actual]]  

---

## 1. Resumen Ejecutivo de Calidad

En cumplimiento estricto del SDLC y de las directrices del rol [[04_qa_engineer]], se implementó y ejecutó una suite automatizada integral basada en `unittest` (Python estándar, sin dependencias de terceros). La suite somete al motor de auditoría a pruebas de estrés financiero, inyección deliberada de anomalías, tolerancia a fallos mediante Dead Letter Queue (DLQ), detección de duplicados temporales y validación de umbrales críticos de descuadre.

### Métricas Globales de Ejecución
- **Total de Tests Automatizados:** 13 pruebas unitarias e integrales
- **Tests Exitosos:** 13 / 13 (100%)
- **Fallos (`failures`):** 0
- **Errores (`errors`):** 0
- **Tiempo de Ejecución:** 0.046 segundos (Holgadamente inferior a la meta RNF-01 de < 2.0 s)
- **Código de Salida:** `0` (SUCCESS)

---

## 2. Matriz de Cobertura de Pruebas (Casos vs. Requisitos)

| ID Requisito | Requisito del Negocio (SRS) | Caso de Prueba Automatizado | Clase de Test (`tests/test_audit_engine.py`) | Estado |
| :--- | :--- | :--- | :--- | :---: |
| **RF-01** | Ingesta y Parseo Multicanal | `test_flujo_completo_con_dataset_real`<br>`test_lote_mixto_separa_validos_e_invalidos_sin_romper` | `TestIntegracionFlujoCompleto`<br>`TestDLQToleranciaFallos` | ✅ PASADO |
| **RF-02** | Detección de Duplicados en Ventana Crítica ($\Delta t \le 180\text{s}$) | `test_duplicados_en_30s_60s_120s`<br>`test_transacciones_fuera_de_ventana_no_son_duplicadas`<br>`test_transacciones_en_ventana_con_diferencias_no_son_duplicadas` | `TestDeteccionDuplicados` | ✅ PASADO |
| **RF-03** | Balance Diario y Custodia de Efectivo | `test_precision_decimal_sin_deriva_flotante`<br>`test_acumulacion_de_fracciones_centecimales`<br>`test_custodia_efectivo_solo_considera_efectivo` | `TestPrecisionMonetaria` | ✅ PASADO |
| **RF-04** | Alerta de Umbral de Descuadre (> 5%) | `test_discrepancia_mayor_al_5_porciento_dispara_alerta`<br>`test_discrepancia_menor_o_igual_al_5_porciento_mantiene_balance_ok`<br>`test_discrepancia_limite_exacto_5_porciento` | `TestUmbralDiscrepancia` | ✅ PASADO |
| **RF-05** | Exportación de Dictamen Markdown para Obsidian | `test_flujo_completo_con_dataset_real` | `TestIntegracionFlujoCompleto` | ✅ PASADO |
| **RF-06** | Aislamiento y Resiliencia ante Datos Corruptos | `test_aislamiento_de_registros_corruptos`<br>`test_empty_dataset_error_lanzado_en_run_full_audit` | `TestDLQToleranciaFallos`<br>`TestDatasetVacio` | ✅ PASADO |
| **RNF-01** | Rendimiento y Latencia (< 2.0 segundos) | Medición de tiempo total de suite (0.046 s) | Global | ✅ PASADO |
| **RNF-02** | Cero Dependencias de Pago / APIs Externas | Ejecución 100% offline con stdlib `unittest` | Global | ✅ PASADO |
| **RNF-03** | Precisión Decimal Exacta (Prohibido float) | `test_precision_decimal_sin_deriva_flotante` | `TestPrecisionMonetaria` | ✅ PASADO |

---

## 3. Detalle de Casos de Prueba Ejecutados

### 3.1 Suite 1: Precisión Monetaria (`TestPrecisionMonetaria`)
- **`test_precision_decimal_sin_deriva_flotante`:** Demuestra que sumas de centavos (0.10 + 0.20) resultan exactamente en `Decimal("0.30")` sin presentar el drift de coma flotante binaria (`0.30000000000000004`).
- **`test_acumulacion_de_fracciones_centecimales`:** Procesa 200 transacciones con montos fraccionarios (S/ 0.33 y S/ 0.67), confirmando que la sumatoria total sea exactamente `Decimal("100.00")` sin perder un solo centavo.
- **`test_custodia_efectivo_solo_considera_efectivo`:** Comprueba la segregación estricta entre efectivo físico y cobros digitales (POS, Yape, Plin), certificando el cálculo exacto del dinero en gaveta física.

### 3.2 Suite 2: Tolerancia a Fallos y DLQ (`TestDLQToleranciaFallos`)
- **`test_aislamiento_de_registros_corruptos`:** Somete al motor a 7 variantes de corrupción deliberada:
  1. Monto negativo (`-100.00`)
  2. Monto cero (`0.00`)
  3. Monto alfanumérico (`"quinientos_soles"`)
  4. Timestamp con formato no ISO (`"FECHA_INVALIDA_2026"`)
  5. Tipo contable inválido (`"prestamo_no_autorizado"`)
  6. Medio de pago fuera de catálogo (`"criptomoneda"`)
  7. Omisión de campo obligatorio (registro sin `categoria`)
  *Resultado:* Los 7 registros fueron aislados en el Dead Letter Queue con su respectivo `dlq_id`, motivo de rechazo y campo incriminado sin abortar la ejecución.
- **`test_lote_mixto_separa_validos_e_invalidos_sin_romper`:** Procesa simultáneamente registros correctos y defectuosos, garantizando que los datos limpios sigan su flujo hacia la auditoría.

### 3.3 Suite 3: Ventana Crítica de Duplicados (`TestDeteccionDuplicados`)
- **`test_duplicados_en_30s_60s_120s`:** Valida que transacciones con idéntico monto, método de pago y referencia separadas por 30 s, 60 s y 120 s sean capturadas con flag de duplicidad dentro de la ventana de 180 s.
- **`test_transacciones_fuera_de_ventana_no_son_duplicadas`:** Certifica que compras idénticas separadas por 200 s (> 180 s) no sean marcadas como duplicadas (evita falsos positivos).
- **`test_transacciones_en_ventana_con_diferencias_no_son_duplicadas`:** Asegura que diferencias en monto, método o referencia desestimen la sospecha de duplicidad.

### 3.4 Suite 4: Evaluación de Discrepancia (`TestUmbralDiscrepancia`)
- **`test_discrepancia_mayor_al_5_porciento_dispara_alerta`:** Descuadre de 8.00% activa el estado `CRITICAL_MISMATCH` y dispara la excepción `DiscrepancyThresholdExceeded` cuando se requiere escalamiento.
- **`test_discrepancia_menor_o_igual_al_5_porciento_mantiene_balance_ok`:** Descuadre de 2.00% permanece dentro del margen de tolerancia y emite veredicto `BALANCE_OK`.
- **`test_discrepancia_limite_exacto_5_porciento`:** Valida el caso límite exacto (5.00%).

### 3.5 Suite 5: Resiliencia ante Datasets Vacíos (`TestDatasetVacio`)
- **`test_empty_dataset_error_lanzado_en_run_full_audit`:** Garantiza que invocar el motor con cero transacciones válidas lance de forma limpia y controlada la excepción `EmptyDatasetError`.

### 3.6 Suite 6: Integración Extremo a Extremo (`TestIntegracionFlujoCompleto`)
- **`test_flujo_completo_con_dataset_real`:** Ejecuta la cadena completa: `DataIngestion` → `SchemaValidator` → `AuditEngine` → `ReportGenerator` utilizando `data/ventas_diarias.csv` y `data/schemas/transactions_schema.json`, verificando la concordancia total con el reporte de producción [[cierre_diario_actual]].

---

## 4. Evidencia de Ejecución en Terminal

```text
test_aislamiento_de_registros_corruptos (test_audit_engine.TestDLQToleranciaFallos.test_aislamiento_de_registros_corruptos) ... ok
test_lote_mixto_separa_validos_e_invalidos_sin_romper (test_audit_engine.TestDLQToleranciaFallos.test_lote_mixto_separa_validos_e_invalidos_sin_romper) ... ok
test_empty_dataset_error_lanzado_en_run_full_audit (test_audit_engine.TestDatasetVacio.test_empty_dataset_error_lanzado_en_run_full_audit) ... ok
test_duplicados_en_30s_60s_120s (test_audit_engine.TestDeteccionDuplicados.test_duplicados_en_30s_60s_120s) ... ok
test_transacciones_en_ventana_con_diferencias_no_son_duplicadas (test_audit_engine.TestDeteccionDuplicados.test_transacciones_en_ventana_con_diferencias_no_son_duplicadas) ... ok
test_transacciones_fuera_de_ventana_no_son_duplicadas (test_audit_engine.TestDeteccionDuplicados.test_transacciones_fuera_de_ventana_no_son_duplicadas) ... ok
test_flujo_completo_con_dataset_real (test_audit_engine.TestIntegracionFlujoCompleto.test_flujo_completo_con_dataset_real) ... ok
test_acumulacion_de_fracciones_centecimales (test_audit_engine.TestPrecisionMonetaria.test_acumulacion_de_fracciones_centecimales) ... ok
test_custodia_efectivo_solo_considera_efectivo (test_audit_engine.TestPrecisionMonetaria.test_custodia_efectivo_solo_considera_efectivo) ... ok
test_precision_decimal_sin_deriva_flotante (test_audit_engine.TestPrecisionMonetaria.test_precision_decimal_sin_deriva_flotante) ... ok
test_discrepancia_limite_exacto_5_porciento (test_audit_engine.TestUmbralDiscrepancia.test_discrepancia_limite_exacto_5_porciento) ... ok
test_discrepancia_mayor_al_5_porciento_dispara_alerta (test_audit_engine.TestUmbralDiscrepancia.test_discrepancia_mayor_al_5_porciento_dispara_alerta) ... ok
test_discrepancia_menor_o_igual_al_5_porciento_mantiene_balance_ok (test_audit_engine.TestUmbralDiscrepancia.test_discrepancia_menor_o_igual_al_5_porciento_mantiene_balance_ok) ... ok

----------------------------------------------------------------------
Ran 13 tests in 0.046s

OK
```

---

## 5. Acta de Certificación de Calidad (Quality Gate)

> [!IMPORTANT]
> **DICTAMEN DE CERTIFICACIÓN QA — PASE A PRODUCCIÓN APROBADO**
> 
> El Agente Ingeniero de Calidad Senior ([[04_qa_engineer]]), tras haber sometido el motor `tools/audit_engine.py` a 13 pruebas automatizadas exhaustivas, certifica que:
> 1. **Precisión Financiera:** Se constató cero desviación numérica en todas las operaciones aritméticas, garantizada por el uso exclusivo de `decimal.Decimal`.
> 2. **Tolerancia y Confiabilidad:** Los registros defectuosos fueron aislados en el DLQ sin provocar interrupciones no programadas ni excepciones no controladas.
> 3. **Detección Determinista:** Los algoritmos de ventana crítica de duplicados y umbral de descuadre respondieron conforme al contrato funcional.
> 4. **Rendimiento Operativo:** El tiempo de respuesta de la suite completa (46 ms) superó con creces el límite contractual de 2 segundos.
> 
> Por lo tanto, el sistema queda formalmente **CERTIFICADO PARA PASE A PRODUCCIÓN**.
> 
> *Firma Simbólica:*  
> **QA Engineer Agent — Lead de Calidad del SDLC**  
> `[[04_qa_engineer]]` · 2026-09-07

---

## Navegación del Proyecto (Obsidian Graph)

| Nodo | Enlace |
| :--- | :--- |
| Inicio del Proyecto | [[README]] |
| ← Fase 4: Implementación | [[04_fase_implementacion]] |
| → Fase 6: Despliegue | [[06_fase_despliegue]] |
| Evidencia de Reporte | [[cierre_diario_actual]] |
| SOP de Auditoría | [[sop_auditoria_caja]] |
| Roles del Equipo | [[01_business_analyst]] · [[02_system_architect]] · [[03_software_engineer]] · [[04_qa_engineer]] |
