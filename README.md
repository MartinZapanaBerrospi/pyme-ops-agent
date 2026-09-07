# PYME Ops Agent

> **Sistema Inteligente y Determinista de Auditoría Operativa y Cierres de Caja para PYMEs**

[![SDLC Phase](https://img.shields.io/badge/SDLC-Fase%201%3A%20Planificaci%C3%B3n-blue)](docs/01_fase_planificacion.md)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)

**Repositorio Oficial**: [https://github.com/MartinZapanaBerrospi/pyme-ops-agent](https://github.com/MartinZapanaBerrospi/pyme-ops-agent)

---

## 📌 Propósito del Proyecto

**PYME Ops Agent** es una solución diseñada para resolver una de las principales brechas operativas en las Pequeñas y Medianas Empresas (PYMEs): la falta de control interno ágil y confiable en la cuadratura diaria de caja y auditoría de transacciones. 

El sistema implementa una **arquitectura híbrida**:
1. **Motores Deterministas en Python (`tools/`)**: Garantizan precisión matemática absoluta (cero alucinación) en la consolidación de ventas, cálculo de comisiones, conciliación cruzada de medios de pago (efectivo, POS, transferencias) y detección de descuadres.
2. **Orquestación Cognitiva por IA & SOPs (`sops/`)**: Contextualiza las discrepancias operativas, evalúa reglas de negocio mediante procedimientos operativos estándar (SOPs) y redacta informes ejecutivos accionables listos para la toma de decisiones sin requerir costos recurrentes de APIs externas.

---

## 👥 Equipo Simulado del Proyecto (Roles SDLC)

Para garantizar el cumplimiento riguroso del Ciclo de Vida del Desarrollo de Software (SDLC), el proyecto es liderado y ejecutado bajo los siguientes roles técnicos:

| Rol | Responsabilidad Principal en el Proyecto |
| :--- | :--- |
| **Software Architect & Project Lead** | Dirección técnica del SDLC, diseño de arquitectura, gobernanza del repositorio y aseguramiento de estándares de ingeniería. |
| **Financial / Operations Specialist (SOP Lead)** | Formalización de procedimientos operativos de caja, reglas de negocio y contratos funcionales de auditoría. |
| **Senior Python Engineer** | Implementación de motores deterministas, validadores de esquemas y herramientas de cálculo de alto rendimiento. |
| **QA & Reliability Engineer** | Diseño de planes de prueba, generación de datasets sintéticos y verificación de tolerancia a fallos y casos borde. |
| **AI Systems & Automation Engineer** | Integración de agentes locales, orquestación de flujos de trabajo en Markdown para Obsidian y automatización de reportes. |

---

## 📂 Arquitectura del Repositorio (Estructura SDLC)

El proyecto sigue una organización limpia y modular diseñada para ser explorada tanto desde el entorno de desarrollo como desde una bóveda de **Obsidian**:

```text
pyme-ops-agent/
├── .obsidian/               # Configuración de bóveda Obsidian para gestión del conocimiento
├── .gitignore               # Exclusiones profesionales para Python y Obsidian
├── README.md                # Presentación general y especificaciones del proyecto
├── docs/                    # Documentación formal de cada fase del SDLC
│   └── 01_fase_planificacion.md
├── sops/                    # Procedimientos operativos estándar y contratos de skills
│   └── .gitkeep
├── tools/                   # Scripts y motores deterministas en Python
│   └── .gitkeep
├── data/                    # Datasets de prueba, esquemas JSON y transacciones de entrada
│   └── .gitkeep
└── reports/                 # Informes ejecutivos generados y actas de auditoría
    └── .gitkeep
```

---

## 🗺️ Estado del Proyecto y Cronograma SDLC

El proyecto se ejecuta siguiendo las 7 fases del SDLC:

- [x] **Fase 1: Planificación** (Arquitectura base, viabilidad, alcance inicial y control de versiones) - *Entregado*
- [ ] **Fase 2: Análisis de Requerimientos** (Historias de usuario, especificación funcional y casos de uso)
- [ ] **Fase 3: Diseño del Sistema** (Arquitectura C4, contratos de tools y schemas de datos)
- [ ] **Fase 4: Implementación** (Desarrollo de motores en Python y generadores de informes)
- [ ] **Fase 5: Pruebas e Integración** (Unit testing, validación de datasets y edge cases)
- [ ] **Fase 6: Despliegue y Puesta en Marcha** (Documentación operativa y guías de ejecución)
- [ ] **Fase 7: Mantenimiento y Evolución** (Métricas, optimizaciones y roadmap)

Para ver el análisis detallado de la fase actual, consulte el documento formal: [`docs/01_fase_planificacion.md`](docs/01_fase_planificacion.md).
