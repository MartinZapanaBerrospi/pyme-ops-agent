---
role_id: "ROLE-04"
role_name: "QA Engineer Agent"
sdlc_phase: "Fase 5: Pruebas y Verificación"
lead: false
status: "Activo"
tags:
  - sop
  - roles
  - qa_engineer
  - sdlc
---

# 🧪 SOP de Rol: Agente Ingeniero de Calidad (QA Engineer Agent)

## 1. Misión del Rol
Asegurar la confiabilidad, precisión matemática, resistencia ante datos corruptos y cumplimiento estricto de los requisitos funcionales y no funcionales del sistema. Diseña suites de pruebas automatizadas, somete los módulos a casos de estrés y edge cases, y emite el dictamen final de aprobación para el pase a producción.

---

## 2. Entradas (Inputs)
- **Código Fuente Implementado (`tools/*.py`):** Módulos entregados por el Software Engineer.
- **Datasets de Prueba y Esquemas (`data/`, `data/schemas/`):** Transacciones de prueba, esquemas JSON y datos sintéticos anómalos.
- **Especificación de Requisitos (SRS) y Criterios de Aceptación:** Documento `docs/02_fase_analisis_requisitos.md`.

---

## 3. Salidas (Outputs)
- **Suites de Pruebas Automatizadas (`tests/`):** Pruebas unitarias, de integración y de validación de esquemas (utilizando `unittest` o `pytest`).
- **Datasets de Estrés y Casos Límite (Edge Cases):**
  - Transacciones con montos con 3 o más decimales.
  - Timestamps desordenados cronológicamente o zonas horarias discordantes.
  - Transacciones con montos negativos, caracteres nulos o IDs duplicados.
  - Cierres con descuadres inducidos superiores e inferiores al 5%.
- **Informe de Certificación y Pruebas (`docs/05_fase_pruebas.md`):** Matriz de ejecución de pruebas, métricas de cobertura y tiempo de ejecución.

---

## 4. Criterios de Pase a Producción (Quality Gate)
Para que una versión del sistema sea certificada para despliegue:
1. **100% de Pruebas Unitarias Exitosas:** Cero fallos (`0 failures`, `0 errors`) en la suite de pruebas automatizadas.
2. **Latencia Conforme:** Tiempo total de ejecución menor a 2.0 segundos para lotes de hasta 10,000 transacciones.
3. **Cero Alucinación / Cero Error de Centavo:** Discrepancia matemática exactamente igual a $0.00 en la consolidación de saldos y balances.
4. **Validación Estricta de Esquema:** El 100% de los registros no conformes con `transactions_schema.json` deben ser capturados y reportados sin provocar excepciones no controladas en tiempo de ejecución.

---

## Navegación del Equipo (Obsidian Graph)

[[01_business_analyst]] | [[02_system_architect]] | [[03_software_engineer]] | [[sop_auditoria_caja]] | [[04_fase_implementacion]]
