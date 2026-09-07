---
title: "Fase 3: Diseño de Arquitectura - PYME Ops Agent"
document_type: "Architecture Design Document (ADD)"
phase: "03 - Diseño del Sistema"
project: "PYME Ops Agent"
author: "System Architect Agent"
status: "Aprobado"
date: 2026-09-07
repository: "https://github.com/MartinZapanaBerrospi/pyme-ops-agent"
tags:
  - sdlc
  - arquitectura
  - c4
  - mermaid
  - diseno
---

# Documento de Diseño Arquitectónico — PYME Ops Agent

> **Proyecto:** PYME Ops Agent  
> **Fase SDLC:** 03 - Diseño del Sistema  
> **Líder de Fase:** System Architect Agent  
> **Revisores:** Business Analyst (validación de requisitos), Software Engineer (viabilidad de implementación), QA Engineer (verificabilidad)

---

## 1. Visión General de la Arquitectura

El sistema adopta un **patrón de arquitectura en capas desacopladas** (Layered + Pipe-and-Filter), donde cada componente tiene responsabilidades únicas y contratos de interfaz explícitos. Esto garantiza la independencia entre la lógica matemática determinista y la capa de presentación/orquestación cognitiva, eliminando el riesgo de alucinación numérica en ambos extremos del flujo.

---

## 2. Diagrama C4 — Nivel 1: Contexto del Sistema

```mermaid
C4Context
    title Nivel 1 — Contexto del Sistema PYME Ops Agent

    Person(operador, "Operador / Cajero", "Registra transacciones diarias en múltiples medios de pago.")
    Person(admin, "Administrador / Dueño PYME", "Supervisa el dictamen de auditoría y toma decisiones.")

    System(pyme_ops_agent, "PYME Ops Agent", "Motor determinista de auditoría y detección de descuadres de caja para PYMEs.")

    System_Ext(obsidian, "Obsidian Vault", "Bóveda de conocimiento local donde se visualizan los reportes ejecutivos generados en Markdown.")
    System_Ext(git_hub, "GitHub Repository", "Control de versiones, trazabilidad de documentación y respaldo remoto del sistema.")

    Rel(operador, pyme_ops_agent, "Carga archivos de transacciones", "CSV/JSON via CLI")
    Rel(pyme_ops_agent, admin, "Entrega dictamen ejecutivo de auditoría", "Markdown Report")
    Rel(pyme_ops_agent, obsidian, "Escribe reportes renderizables", "Markdown (.md)")
    Rel(pyme_ops_agent, git_hub, "Versiona artefactos del sistema", "Git Push")
```

---

## 3. Diagrama C4 — Nivel 2: Contenedores del Sistema

```mermaid
C4Container
    title Nivel 2 — Contenedores del Sistema PYME Ops Agent

    Person(operador, "Operador de Caja", "Carga archivos de transacciones.")
    Person(admin, "Administrador PYME", "Revisa reportes de auditoría.")

    Container_Boundary(pyme_ops, "PYME Ops Agent — Sistema Local") {
        Container(cli, "CLI Orquestador", "Python / argparse", "Punto de entrada principal. Valida argumentos, coordina el flujo de datos y gestiona el ciclo de vida de la auditoría.")
        Container(validator, "Módulo Validador de Esquemas", "Python / jsonschema", "Valida cada registro entrante contra el contrato JSON Schema formal. Aísla registros corruptos al Dead Letter Queue.")
        Container(audit_engine, "Motor de Auditoría (audit_engine.py)", "Python puro / decimal.Decimal", "Núcleo determinista: concilia transacciones, detecta duplicados, calcula balances netos y evalúa umbrales de descuadre.")
        Container(report_gen, "Generador de Reportes", "Python / pathlib / string templates", "Produce el informe ejecutivo en Markdown estructurado con tablas, KPIs, alertas y metadatos YAML para Obsidian.")
        Container(dlq, "Dead Letter Queue (DLQ)", "Archivo de log local / JSON Lines", "Almacena en cuarentena los registros inválidos, corruptos o no conformes para revisión manual posterior.")
    }

    ContainerDb(data_in, "data/input/", "CSV / JSON", "Archivos de transacciones operativas diarias cargados por el operador.")
    ContainerDb(schemas, "data/schemas/", "JSON Schema", "Contrato formal de validación de datos (transactions_schema.json).")
    ContainerDb(reports_out, "reports/", "Markdown (.md)", "Repositorio de dictámenes ejecutivos de auditoría generados.")

    System_Ext(obsidian, "Obsidian Vault", "Renderiza los reportes Markdown como notas del conocimiento.")

    Rel(operador, cli, "Ejecuta auditoría via CLI", "--input, --schema, --output, --tolerance")
    Rel(cli, data_in, "Lee archivos de transacciones", "pathlib.Path")
    Rel(cli, schemas, "Carga esquema de validación", "json.load")
    Rel(cli, validator, "Delega validación de registros", "list[dict]")
    Rel(validator, dlq, "Envía registros inválidos", "JSON Lines append")
    Rel(validator, audit_engine, "Entrega registros válidos", "list[Transaction]")
    Rel(audit_engine, report_gen, "Entrega AuditResult consolidado", "AuditResult dataclass")
    Rel(report_gen, reports_out, "Escribe dictamen ejecutivo", "AUDIT_YYYY-MM-DD.md")
    Rel(reports_out, obsidian, "Renderiza reporte", "Markdown nativo")
    Rel(report_gen, admin, "Notifica dictamen de auditoría", "Markdown Report")
```

---

## 4. Diagrama de Flujo de Datos — Pipe-and-Filter

```mermaid
flowchart TD
    A["📂 data/input/transactions.csv\n(Fuente de datos operativos)"]
    B["⚙️ CLI Orquestador\naudit_engine.py --input ... --schema ..."]
    C{"🔍 Validador de Esquemas\n¿Registro conforme a\ntransactions_schema.json?"}
    D["✅ Registros Válidos\nlist[Transaction]"]
    E["☠️ Dead Letter Queue\ndata/dlq/YYYY-MM-DD_anomalies.jsonl"]
    F["🧮 Motor de Auditoría\ndetect_duplicates()\ncalculate_balance()\nevaluate_thresholds()"]
    G{"⚠️ ¿Descuadre crítico?\nDiscrepancia > tolerance%"}
    H["🟥 AuditResult con\nCRITICAL_MISMATCH"]
    I["🟩 AuditResult con\nBALANCE_OK"]
    J["📝 Generador de Reportes\nMarkdown + YAML frontmatter"]
    K["📁 reports/AUDIT_YYYY-MM-DD.md\n(Dictamen Ejecutivo Final)"]
    L["🔮 Obsidian Vault\nVisualización & Indexación"]

    A --> B
    B --> C
    C -- Válido --> D
    C -- Inválido / Corrupto --> E
    D --> F
    F --> G
    G -- Sí --> H
    G -- No --> I
    H --> J
    I --> J
    J --> K
    K --> L
```

---

## 5. Patrón de Diseño: Separación Estricta de Capas

El diseño se fundamenta en la separación en dos capas funcionalmente independientes y contractualmente aisladas:

### Capa 1 — Núcleo Determinista (Python CLI Idempotente)
| Atributo | Especificación |
| :--- | :--- |
| **Responsabilidad** | Toda computación matemática: suma, detección de duplicados, evaluación de umbrales y consolidación de balances. |
| **Garantía Nuclear** | La misma entrada siempre produce la misma salida. **Cero estado mutable global**. Funciones puras. |
| **Tipo de Dato Monetario** | `decimal.Decimal` con `ROUND_HALF_UP` a 2 decimales. `float` estrictamente prohibido. |
| **Dependencias** | Exclusivamente librería estándar de Python 3.10+ (`json`, `csv`, `decimal`, `datetime`, `pathlib`, `dataclasses`, `typing`). |
| **Interfaz de Ejecución** | CLI mediante `argparse`. No expone API HTTP ni requiere daemon o servicio de fondo. |
| **Idempotencia** | Ejecutar el motor N veces con el mismo input produce siempre el mismo reporte de output idéntico bit-a-bit. |

### Capa 2 — Interfaz Cognitiva y de Visualización (Obsidian + Agentes)
| Atributo | Especificación |
| :--- | :--- |
| **Responsabilidad** | Renderizado visual de reportes, indexación de conocimiento, orquestación de agentes y navegación contextual. |
| **Tecnología** | Markdown (CommonMark/GFM), Obsidian Vault, SOP Documents y agentes de lenguaje natural. |
| **Punto de Integración** | La Capa 2 **consume únicamente artefactos Markdown** escritos por la Capa 1. **No ejecuta cálculos financieros directamente**. |
| **Cero Contaminación Cruzada** | Ningún módulo de la Capa 1 importa librerías de IA, modelos de lenguaje o dependencias de la Capa 2. |

---

## 6. Estrategia de Manejo de Errores y Tolerancia a Fallos

El sistema adopta una política de **Fail-Fast + Aislamiento con Dead Letter Queue (DLQ)**, garantizando que los registros corruptos nunca contaminen los cálculos del núcleo determinista.

### 6.1 Taxonomía de Errores y Respuestas del Sistema

| Tipo de Error | Ejemplo Concreto | Respuesta del Sistema | Destino |
| :--- | :--- | :--- | :--- |
| **Campo obligatorio ausente** | Registro sin `monto` o sin `tipo` | Registro aislado, `DataValidationError` logged | DLQ |
| **Tipo de dato incompatible** | `monto: "veinte"` (string en lugar de number) | Conversión fallida, error capturado, aislado | DLQ |
| **Timestamp inválido** | `"2026-13-45T99:99"` o zona horaria ausente | Rechazo estricto con mensaje de error específico | DLQ |
| **Enum fuera de dominio** | `metodo_pago: "bitcoin"` | `DataValidationError` con campo y valor incriminado | DLQ |
| **Monto negativo o cero** | `monto: -150.00` | Violación de contrato `exclusiveMinimum: 0`, aislado | DLQ |
| **Duplicado temporal** | Mismo monto+método+referencia en ≤ 180s | Marcado con flag `DUPLICATE_SUSPECTED`, incluido en reporte de alertas | Alerta |
| **Descuadre crítico** | Discrepancia > 5% | `DiscrepancyThresholdExceeded` raised, alerta `CRITICAL_MISMATCH` en reporte | Reporte |
| **Archivo de entrada vacío** | 0 registros válidos procesados | Ejecución terminada, error explícito `EmptyDatasetError` en log | Log CLI |

### 6.2 Estructura del Dead Letter Queue (DLQ)
Los registros inválidos se almacenan en `data/dlq/YYYY-MM-DD_anomalies.jsonl` en formato JSON Lines, con la siguiente estructura de envelope:

```json
{
  "dlq_id": "DLQ-20260907-001",
  "timestamp_registro": "2026-09-07T14:30:00Z",
  "motivo_rechazo": "Campo 'monto' con valor no numérico: 'veinte'",
  "campo_incriminado": "monto",
  "valor_recibido": "veinte",
  "registro_original": { "id_transaccion": "TRX-001", "monto": "veinte", "..." : "..." }
}
```

---

## 7. Estrategia de Persistencia y Directorios

```text
pyme-ops-agent/
├── data/
│   ├── input/           # Archivos de transacciones operativas (inmutables en tiempo de ejecución)
│   ├── schemas/         # Contratos formales de validación JSON Schema
│   └── dlq/             # Dead Letter Queue — registros anómalos cuarentenados
├── tools/               # Motores deterministas Python (Capa 1)
│   ├── audit_engine.py  # Motor principal de auditoría
│   ├── validator.py     # Validador de esquemas y tipos
│   └── report_gen.py    # Generador de reportes Markdown
└── reports/             # Dictámenes ejecutivos de auditoría generados (Capa 2 → Obsidian)
```

---

## 8. Criterios de Aceptación de la Fase 3
1. [x] Diagramas C4 Nivel 1 (Contexto) y Nivel 2 (Contenedores) en Mermaid.js documentados.
2. [x] Diagrama de flujo Pipe-and-Filter de extremo a extremo.
3. [x] Separación de capas formalmente definida con atributos técnicos verificables.
4. [x] Taxonomía completa de errores y política DLQ documentada.
5. [x] Contrato de interfaces del motor definido en `tools/audit_engine_spec.py`.
6. [x] SOP operativo del skill `audit_pyme_cashflow` creado en `sops/`.
