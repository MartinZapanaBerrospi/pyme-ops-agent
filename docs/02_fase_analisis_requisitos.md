---
title: "Fase 2: Análisis de Requisitos - PYME Ops Agent"
document_type: "Software Requirements Specification (SRS)"
phase: "02 - Análisis de Requisitos"
project: "PYME Ops Agent"
author: "Business Analyst Agent"
status: "Aprobado"
date: 2026-09-07
repository: "https://github.com/MartinZapanaBerrospi/pyme-ops-agent"
tags:
  - sdlc
  - requisitos
  - srs
  - raci
  - pyme
---

# Documento de Especificación de Requisitos de Software (SRS)

> **Proyecto:** PYME Ops Agent  
> **Fase SDLC:** 02 - Análisis de Requisitos  
> **Líder de Fase:** Business Analyst Agent  
> **Revisores:** System Architect, Software Engineer, QA Engineer  

---

## 1. Objetivo del Sistema
El **PYME Ops Agent** tiene como objetivo principal constituirse como un **Motor Determinista de Auditoría Financiera Operativa y Detección de Descuadres de Caja**, permitiendo a las Pequeñas y Medianas Empresas (PYMEs):
1. Consolidar e inspeccionar de manera automatizada las operaciones diarias multicanal (efectivo, cobros digitales y terminales POS).
2. Aislar con exactitud matemática discrepancias, transacciones repetidas y desfases de comisiones.
3. Generar un acta de cuadre e informe ejecutivo en Markdown nativo para visualización e indexación en bóvedas de conocimiento (Obsidian), mitigando pérdidas y reduciendo los tiempos de cierre diario de horas a segundos.

---

## 2. Requisitos Funcionales (RF)

| ID | Nombre | Descripción Técnica y Criterio de Aceptación | Prioridad |
| :--- | :--- | :--- | :--- |
| **RF-01** | **Ingesta y Parseo Multicanal** | El sistema debe validar e ingerir datasets de transacciones en formato JSON/CSV que contengan cobros y desembolsos a través de medios de pago diferenciados: `efectivo`, `yape`, `plin` y `pos`. Debe rechazar o aislar registros que no cumplan el esquema formal. | **Alta (Must Have)** |
| **RF-02** | **Detección de Duplicados en Ventana Crítica** | El motor debe identificar transacciones redundantes definidas por: mismo monto, mismo método de pago y misma referencia/cliente dentro de una ventana temporal crítica ajustable ($\Delta t \le 180\text{ segundos}$). Cada duplicado debe ser marcado como flag de alerta. | **Alta (Must Have)** |
| **RF-03** | **Cálculo de Balance Diario y Custodia** | El sistema calculará de forma exacta: <br>$$\text{Total Ingresos} = \sum \text{Monto}_{\text{ingresos}}$$ <br>$$\text{Total Egresos} = \sum \text{Monto}_{\text{egresos}}$$ <br>$$\text{Balance Neto} = \text{Total Ingresos} - \text{Total Egresos}$$ <br>Además, calculará el **Monto en Custodia Física** (exclusivo efectivo en caja neta). | **Alta (Must Have)** |
| **RF-04** | **Alerta de Umbral de Descuadre Crítico** | El motor comparará el balance calculado frente al arqueo/declaración de cierre físico. Si la discrepancia absoluta porcentual excede el 5% ($$\frac{|\text{Calculado} - \text{Declarado}|}{\text{Calculado}} > 0.05$$), el sistema emitirá una alerta crítica con nivel de severidad `CRITICAL_MISMATCH`. | **Alta (Must Have)** |
| **RF-05** | **Exportación de Resumen Ejecutivo en Markdown** | Generación de un informe final de auditoría estructurado en Markdown (`reports/AUDIT_YYYY-MM-DD.md`) con tablas de conciliación, KPIs clave, listado de anomalías y callouts compatibles al 100% con la visualización en Obsidian. | **Alta (Must Have)** |
| **RF-06** | **Auditoría de Egresos y Retiros de Caja** | Clasificación y trazabilidad de todos los egresos registrados durante la jornada (gastos operativos, adelantos, pagos a proveedores y retiros no justificados), emitiendo el porcentaje de absorción de ingresos por gastos directos de caja chica. | **Media (Should Have)** |

---

## 3. Requisitos No Funcionales (RNF)

| ID | Requisito | Métrica / Estándar de Conformidad |
| :--- | :--- | :--- |
| **RNF-01** | **Rendimiento y Determinismo** | El motor de cálculo en Python debe procesar un volumen de hasta 10,000 transacciones en un tiempo total de ejecución inferior a **2.0 segundos** ($\le 2\text{ s}$) en hardware estándar. Las funciones matemáticas deben ser puras y reproducibles. |
| **RNF-02** | **Cero Dependencia de APIs de Pago** | El núcleo de cálculo, conciliación y auditoría operará **100% local y offline**, sin requerir tokens, suscripciones ni llamadas de red a APIs externas de pago (OpenAI, Anthropic u otras pasarelas propietarias). |
| **RNF-03** | **Integridad Financiera Local** | Toda operación monetaria se procesará bajo tipado `decimal.Decimal` con precisión de 2 a 4 decimales. Prohibido el uso de coma flotante binaria (`float`). Los datos de origen no serán mutados en disco (inmutabilidad de inputs). |
| **RNF-04** | **Trazabilidad y Compatibilidad Obsidian** | Todos los artefactos de especificación, configuración y reportes finales deben cumplir el estándar CommonMark/GitHub Flavored Markdown compatible con los motores de renderizado de Obsidian Vault y versionados bajo Git. |

---

## 4. Matriz RACI de Roles de Agentes

Definición de responsabilidades para el ciclo de vida del desarrollo:
- **R (Responsible):** El rol que ejecuta y construye el entregable.
- **A (Accountable):** El rol que aprueba y rinde cuentas por la calidad final.
- **C (Consulted):** El rol con el que se consulta y colabora bidireccionalmente.
- **I (Informed):** El rol que es notificado del resultado y avances.

| Entregable / Actividad SDLC | Business Analyst | System Architect | Software Engineer | QA Engineer |
| :--- | :---: | :---: | :---: | :---: |
| **Especificación de Requisitos (SRS / ERS)** | **R / A** | C | I | C |
| **Contrato de Datos (`schemas/*.json`)** | **R** | A | C | C |
| **Arquitectura y Diseño C4 (`docs/03_...`)** | C | **R / A** | C | I |
| **Especificación de Interfaces de Tools** | I | **R / A** | C | C |
| **Implementación de Motores Python (`tools/`)** | I | C | **R / A** | C |
| **Generador de Reportes Obsidian** | C | C | **R** | A |
| **Diseño y Ejecución de Pruebas Unitarias** | I | I | C | **R / A** |
| **Datasets de Estrés y Edge Cases** | C | I | I | **R / A** |
| **Certificación de Pase a Producción** | C | C | I | **R / A** |

---

## 5. Criterios de Aceptación de la Fase 2
1. [x] Creación formal de fichas de roles en `sops/roles/` para BA, Arquitecto, Dev y QA.
2. [x] Especificación completa de 6 Requisitos Funcionales (RF-01 a RF-06).
3. [x] Especificación de 4 Requisitos No Funcionales críticos (RNF-01 a RNF-04).
4. [x] Establecimiento de la Matriz RACI para gobernanza inter-agentes.
5. [x] Formalización del contrato de datos en `data/schemas/transactions_schema.json`.
