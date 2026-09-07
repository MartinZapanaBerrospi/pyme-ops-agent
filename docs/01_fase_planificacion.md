---
title: "Fase 1: Planificación - PYME Ops Agent"
document_type: "SDLC Phase Deliverable"
phase: "01 - Planificación"
project: "PYME Ops Agent"
lead: "Software Architect & Project Lead"
status: "Aprobado / Completado"
date: 2026-09-07
repository: "https://github.com/MartinZapanaBerrospi/pyme-ops-agent"
tags:
  - sdlc
  - planificacion
  - arquitectura
  - pyme
  - auditoria
---

# Documento de Entregable: Fase 1 - Planificación

> **Proyecto:** PYME Ops Agent  
> **Fase SDLC:** 01 - Planificación y Definición Inicial  
> **Líder Técnico:** Software Architect & Project Lead  
> **Repositorio Oficial:** [pyme-ops-agent](https://github.com/MartinZapanaBerrospi/pyme-ops-agent)

---

## 1. Propósito y Justificación del Sistema

### 1.1 Contexto Operativo y Problemática
En el ecosistema de las Pequeñas y Medianas Empresas (PYMEs), el control de las operaciones diarias de caja adolece tradicionalmente de vulnerabilidades críticas:
- **Conciliación manual propensa a error humano:** Los cierres de turno y de día suelen realizarse de manera manual o mediante hojas de cálculo fragmentadas, lo que incrementa el riesgo de transposición numérica, omisión de comprobantes y errores de tipeo.
- **Diversidad de medios de pago no integrados:** La coexistencia de transacciones en efectivo, terminales de pago (POS de diferentes adquirentes), billeteras digitales y transferencias directas genera descuadres difíciles de rastrear al final de la jornada.
- **Fuga silenciosa de capital y descalce:** Las discrepancias no detectadas a tiempo (diferencias de centavos recurrentes, comisiones no deducidas, transacciones anuladas indebidamente) terminan representando pérdidas materiales acumuladas a fin de mes.
- **Sobrecarga de gestión administrativa:** Los dueños de negocios o administradores dedican entre 2 a 3 horas diarias únicamente a contrastar comprobantes físicos contra reportes bancarios y cuadres de terminales.

### 1.2 Justificación y Propuesta de Valor
**PYME Ops Agent** nace como un sistema diseñado para dotar a cualquier PYME de un departamento de auditoría operativa automatizado, riguroso y de respuesta inmediata:
1. **Auditoría Instantánea:** Procesa y cruza en cuestión de segundos el registro de transacciones individuales frente al reporte de cierre de caja declarado.
2. **Imparcialidad y Trazabilidad:** Cada cálculo se audita mediante reglas explícitas y genera actas operativas estandarizadas en Markdown (compatibles con Obsidian y exportables a PDF/HTML).
3. **Reducción de Costes Operativos:** Libera el 90% del tiempo dedicado a la cuadratura manual y proporciona alertas tempranas ante anomalías financieras o sospechas de fraude interno.

---

## 2. Análisis de Viabilidad

### 2.1 Viabilidad Técnica: Arquitectura Híbrida Determinista-Cognitiva
El reto clásico de integrar modelos de Inteligencia Artificial en entornos contables es la susceptibilidad a la **alucinación numérica** (errores de suma o deducción errónea de montos). Por ello, la viabilidad técnica del sistema se asienta sobre un **paradigma arquitectónico híbrido de dos capas desacopladas**:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        PYME Ops Agent - Híbrido                         │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
       ┌───────────────────────────┴───────────────────────────┐
       ▼                                                       ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│     Capa 1: Determinista      │               │      Capa 2: Cognitiva        │
│       (Python Puro / Core)    │               │    (Orquestación & SOPs)      │
├───────────────────────────────┤               ├───────────────────────────────┤
│ • Motores de cálculo exacto   │               │ • Interpretación de negocio   │
│ • Conciliación matemática     │ ──[Reporte]──►│ • Evaluación de contexto      │
│ • Detección de duplicados     │   Auditado    │ • Aplicación de directrices   │
│ • Validación de tipos/schemas │               │ • Redacción ejecutiva final   │
└───────────────────────────────┘               └───────────────────────────────┘
```

1. **Capa 1: Motor Determinista en Python (`tools/`)**:
   - Ejecuta todas las operaciones matemáticas, sumatorias de lotes, detección de márgenes de tolerancia y desajustes de centavos con precisión flotante/decimal estricta (`decimal.Decimal`).
   - Cero riesgo de alucinación: si una transacción no cuadra por \$0.50, el script emite el valor exacto y la identificación de la fila anómala.
   - Sin dependencias pesadas: se priorizan librerías estándar (`csv`, `json`, `dataclasses`, `datetime`, `decimal`) garantizando compatibilidad y velocidad de ejecución en cualquier sistema operativo.

2. **Capa 2: Orquestación Cognitiva y SOPs (`sops/`)**:
   - La IA interviene exclusivamente como auditor cualitativo y relator ejecutivo: interpreta el reporte de discrepancias generado por la Capa 1, lo contrasta contra los Procedimientos Operativos Estándar (SOPs) de la empresa y genera la conclusión gerencial.
   - **Cero coste en consumo de APIs externas:** La solución se concibe para operar mediante entornos de agentes locales (como asistentes IDE integrados, CLI open source o modelos cuantizados locales), eliminando barreras de pago por tokens para la PYME.

### 2.2 Viabilidad Económica y Retorno de Inversión (ROI)
- **Coste de Adquisición / Licenciamiento:** \$0.00 USD (construido sobre tecnologías de código abierto: Python, Git y Markdown).
- **Coste de Infraestructura:** \$0.00 USD en etapa inicial (ejecución directa en la estación de trabajo local o laptop del responsable del negocio).
- **Ahorro Estimado:**
  - Reducción de ~12 a 15 horas hombre semanales dedicadas a cuadres manuales.
  - Mitigación directa de pérdidas por redondeo o transacciones dobles (estimada en un 1% a 3% de la facturación mensual en comercios minoristas).
- **Conclusión de Viabilidad:** El proyecto es **100% viable y altamente rentable**, presentando un umbral de retorno inmediato desde el primer mes de uso del MVP.

---

## 3. Definición del Alcance

### 3.1 Alcance del Producto Mínimo Viable (MVP)
El MVP abordará el flujo crítico de cierre de ventas diario y auditoría de turnos para un establecimiento con uno o múltiples puntos de venta (POS):

- [x] **Arquitectura Base del Repositorio:** Estructura modular SDLC con control de versiones y trazabilidad de documentación.
- [ ] **Esquemas de Entrada Estandarizados (`data/`):**
  - Dataset de transacciones operativas individuales (ventas registradas con identificador, método de pago, monto, comisión, fecha/hora).
  - Dataset de declaración de cierre de caja por turno/día (montos declarados por cajero según efectivo, voucher POS y transferencias).
- [ ] **Procedimientos Operativos Estándar (`sops/`):**
  - SOP-001: Directrices para la auditoría de caja chica, tolerancia a descuadres mínimos y escalamiento de faltantes.
- [ ] **Herramientas Deterministas (`tools/`):**
  - Validador sintáctico y semántico de datos de entrada.
  - Motor de conciliación cruzada de métodos de pago y cálculo de diferencias netas.
  - Identificador de anomalías (transacciones repetidas, importes negativos, desajustes de comisiones).
- [ ] **Generador de Reportes Ejecutivos (`reports/`):**
  - Producción automática de dictamen de auditoría en formato Markdown estructurado con resumen de indicadores (KPIs de ventas, total conciliado, alertas críticas).

### 3.2 Exclusiones Explícitas (Fuera de Alcance para el MVP)
Para mantener un enfoque ágil y control de complejidad, se declaran fuera del alcance del MVP las siguientes características:
- Integración en tiempo real mediante webhooks o APIs bancarias privadas (Open Banking).
- Facturación electrónica directa con entidades tributarias fiscales (e.g., SUNAT, SAT, DIAN).
- Interfaz gráfica de usuario web/móvil compleja (se interactúa mediante terminal/agente local y Obsidian).
- Esquema multi-empresa con roles de acceso concurrentes distribuidos en la nube.

---

## 4. Cronograma de Fases SDLC (Ciclo de Vida Completo)

El proyecto se rige por un modelo iterativo e incremental basado en 7 fases formales:

| Fase SDLC | Denominación | Entregables Principales | Estado |
| :--- | :--- | :--- | :--- |
| **Fase 1** | **Planificación** | • Repositorio Git inicializado y `.gitignore` optimizado.<br>• Estructura de directorios SDLC (`docs`, `sops`, `tools`, `data`, `reports`).<br>• `README.md` formal del proyecto.<br>• Documento de viabilidad, propósito y cronograma (`01_fase_planificacion.md`). | **Completado** |
| **Fase 2** | **Análisis de Requerimientos** | • Matriz de requerimientos funcionales (RF) y no funcionales (RNF).<br>• Historias de usuario (User Stories) y criterios de aceptación.<br>• Documento `02_fase_requerimientos.md`. | *Pendiente* |
| **Fase 3** | **Diseño del Sistema** | • Especificación de contratos de interfaces y APIs de tools.<br>• Definición de esquemas de datos JSON/CSV (`data/schemas`).<br>• Formalización de SOP-001 en `sops/`.<br>• Documento `03_fase_diseno.md`. | *Pendiente* |
| **Fase 4** | **Implementación** | • Módulos Python en `tools/` (conciliador, parser, auditor).<br>• Generador de reportes ejecutivos para `reports/`.<br>• Documento `04_fase_implementacion.md`. | *Pendiente* |
| **Fase 5** | **Pruebas y Verificación** | • Suite de pruebas unitarias (`tests/`) con cobertura de casos borde.<br>• Dataset sintético de estrés y anomalías inducidas.<br>• Matriz de pruebas y documento `05_fase_pruebas.md`. | *Pendiente* |
| **Fase 6** | **Despliegue y Operación** | • Guía de instalación y manual del operador de caja/auditor.<br>• Configuración de ejecución en un clic vía CLI.<br>• Documento `06_fase_despliegue.md`. | *Pendiente* |
| **Fase 7** | **Mantenimiento y Evolución** | • Bitácora de incidencias y lecciones aprendidas.<br>• Roadmap de evolución a integraciones bancarias.<br>• Documento `07_fase_mantenimiento.md`. | *Pendiente* |

---

## 5. Criterios de Aceptación de la Fase 1
Para considerar aprobada la Fase 1:
1. [x] Control de versiones inicializado en la rama principal.
2. [x] `.gitignore` protegiendo entornos virtuales, temporales de Python y cachés de Obsidian.
3. [x] Directorios operativos creados y rastreados mediante Git.
4. [x] `README.md` estructurado y documentado con la identidad del proyecto.
5. [x] Documento formal de planificación redactado y verificado.
6. [x] Commit de cierre de fase ejecutado bajo convención de commits semánticos (`chore(sdlc): ...`).

---

## Navegación del Proyecto (Obsidian Graph)

| Nodo | Enlace |
| :--- | :--- |
| Inicio del Proyecto | [[README]] |
| → Fase 2: Análisis | [[02_fase_analisis_requisitos]] |
| → Fase 3: Diseño | [[03_fase_diseno_arquitectura]] |
| → Fase 4: Implementación | [[04_fase_implementacion]] |
| SOP Auditoría | [[sop_auditoria_caja]] |
