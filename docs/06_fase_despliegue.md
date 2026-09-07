---
title: "Fase 6: Despliegue (Deployment) - PYME Ops Agent"
document_type: "Deployment Guide & MCP Specification"
phase: "06 - Despliegue y Puesta en Marcha"
project: "PYME Ops Agent"
author: "Lead DevOps & Software Architect"
status: "Desplegado / En Producción"
date: 2026-09-07
repository: "https://github.com/MartinZapanaBerrospi/pyme-ops-agent"
tags:
  - sdlc
  - despliegue
  - mcp
  - devops
  - produccion
---

# Documento de Entregable: Fase 6 — Despliegue (Deployment)

> **Proyecto:** PYME Ops Agent  
> **Fase SDLC:** 06 - Despliegue y Puesta en Marcha  
> **Responsables:** Lead DevOps Agent & Software Architect Agent  
> **Fase Precedente:** [[05_fase_pruebas]] (Certificación QA aprobada)  
> **Artefactos Operativos:** [[cierre_diario_actual]] | [[sop_auditoria_caja]]  

---

## 1. Visión General del Despliegue

La **Fase 6** materializa la puesta en marcha operativa del sistema mediante una **estrategia de doble canal de consumo**:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PYME Ops Agent - En Producción                     │
└───────────────────────────────────────┬─────────────────────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│     Canal 1: Usuario Final    │               │    Canal 2: Agentes & LLMs    │
│        (Pyme / Operador)      │               │     (Model Context Protocol)  │
├───────────────────────────────┤               ├───────────────────────────────┤
│ • Lanzador Windows (.bat)     │               │ • Servidor MCP sobre stdio    │
│ • Ejecución con un solo clic  │               │ • Integración Antigravity /   │
│ • Apertura automática de acta │               │   Claude Desktop / Cursor     │
│ • Cero configuración técnica  │               │ • JSON-RPC 2.0 determinista   │
└───────────────────────────────┘               └───────────────────────────────┘
```

1. **Canal Operativo PYME (`deploy/run_audit.bat`):** Script de ejecución en un clic para dueños de negocio o cajeros que valida el entorno, audita la jornada y abre automáticamente el informe ejecutivo.
2. **Canal Cognitivo MCP (`tools/mcp_server.py` + `.mcp/pyme_ops_mcp.json`):** Servidor conforme al estándar industrial **Model Context Protocol (MCP)** para permitir que agentes de IA orquesten auditorías bajo demanda sin coste de APIs externas.

---

## 2. Manual de Despliegue en Estaciones de Trabajo PYME

### 2.1 Requisitos Mínimos del Sistema
- **Sistema Operativo:** Windows 10 / Windows 11 (64-bit), macOS 12+ o Ubuntu 20.04+.
- **Runtime:** Python 3.10 o superior (disponible globalmente en el `PATH`).
- **Espacio en Disco:** < 50 MB (sin entornos virtuales pesados ni dependencias externas de terceros).
- **Memoria RAM:** 512 MB disponible para la ejecución.

### 2.2 Guía de Instalación y Ejecución en Windows
1. **Descarga / Clonación:**
   Clonar o descargar la carpeta del repositorio en la estación de trabajo:
   ```cmd
   git clone https://github.com/MartinZapanaBerrospi/pyme-ops-agent.git
   cd pyme-ops-agent
   ```
2. **Verificación de Python:**
   El lanzador `deploy/run_audit.bat` realiza una comprobación automática previa. Si Python no está en el `PATH`, emite una alerta guiada para su instalación desde [python.org](https://www.python.org/downloads/).
3. **Ejecución Diaria (Cierre de Caja):**
   - El cajero o administrador simplemente hace **doble clic en `deploy/run_audit.bat`**.
   - El script ejecuta el motor de auditoría con la tolerancia configurada (`5.0%`).
   - Muestra el veredicto en consola (`BALANCE CONFORME [OK]` o `CRITICAL_MISMATCH`).
   - Abre de forma inmediata el informe ejecutivo generado en `reports/cierre_diario_actual.md` en el visor predeterminado (Obsidian, VS Code o Bloc de Notas).

---

## 3. Especificación Técnica del Servidor MCP (`tools/mcp_server.py`)

El servidor MCP expone las capacidades deterministas del sistema hacia cualquier cliente compatible con el estándar abierto **Model Context Protocol (MCP)** mediante transporte estándar `stdio`.

### 3.1 Arquitectura del Servidor
- **Protocolo:** JSON-RPC 2.0 sobre `sys.stdin` / `sys.stdout`.
- **Versión de Protocolo MCP:** `2024-11-05`.
- **Aislamiento de Flujos:** Los logs de depuración y diagnósticos se emiten exclusivamente a `sys.stderr`, garantizando que `sys.stdout` permanezca 100% puro para payloads JSON-RPC.

### 3.2 Catálogo de Herramientas Expuestas

#### Tool: `audit_pyme_cashflow`
Audita transacciones de ventas diarias de una PYME, detecta cobros duplicados en ventana de tiempo y genera reporte financiero en Markdown.

**Esquema de Entrada (`inputSchema`):**
```json
{
  "type": "object",
  "properties": {
    "input_csv": {
      "type": "string",
      "description": "Ruta del archivo CSV de transacciones a auditar."
    },
    "output_md": {
      "type": "string",
      "description": "Ruta destino para el reporte Markdown generado.",
      "default": "reports/cierre_diario_actual.md"
    },
    "tolerance": {
      "type": "number",
      "description": "Umbral de tolerancia de descuadre porcentual (0 - 100).",
      "default": 5.0
    },
    "declared": {
      "type": "number",
      "description": "Monto declarado en arqueo físico de caja (opcional)."
    }
  },
  "required": ["input_csv"]
}
```

### 3.3 Métodos JSON-RPC Soportados
| Método | Propósito | Formato de Respuesta |
| :--- | :--- | :--- |
| `initialize` | Handshake de inicialización MCP | Protocolo `2024-11-05`, capacidades de tools y serverInfo. |
| `notifications/initialized` | Confirmación de conexión | Notificación sin retorno. |
| `ping` | Verificación de liveness | Objeto vacío `{}`. |
| `tools/list` | Descubrimiento de herramientas | Array con la especificación de `audit_pyme_cashflow`. |
| `tools/call` | Ejecución de la auditoría | Objeto MCP con bloque `content` de tipo `text`. |

---

## 4. Manifiesto de Configuración MCP (`.mcp/pyme_ops_mcp.json`)

Para integrar el servidor en **Google Antigravity**, **Claude Desktop**, **Cursor** u otros clientes MCP:

```json
{
  "$schema": "https://json.schemastore.org/mcp-settings.json",
  "mcpServers": {
    "pyme-ops-agent": {
      "command": "python",
      "args": [
        "tools/mcp_server.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      },
      "description": "Servidor MCP de PYME Ops Agent — Motor determinista de auditoría de ventas, cierres de caja y detección de descuadres."
    }
  }
}
```

---

## 5. Evidencia de la Prueba de Despliegue (Smoke Test de Producción)

### 5.1 Prueba del Manifiesto `tools/list` vía JSON-RPC:
**Entrada (stdin):**
```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
```

**Respuesta recibida (stdout):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "audit_pyme_cashflow",
        "description": "Audita transacciones de ventas diarias de una PYME, detecta cobros duplicados en ventana de tiempo y genera reporte financiero en Markdown.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "input_csv": {
              "type": "string",
              "description": "Ruta del archivo CSV de transacciones a auditar."
            },
            "output_md": {
              "type": "string",
              "description": "Ruta destino para el reporte Markdown generado.",
              "default": "reports/cierre_diario_actual.md"
            },
            "tolerance": {
              "type": "number",
              "description": "Umbral de tolerancia de descuadre porcentual (0 - 100).",
              "default": 5.0
            },
            "declared": {
              "type": "number",
              "description": "Monto declarado en arqueo físico de caja (opcional)."
            }
          },
          "required": [
            "input_csv"
          ]
        }
      }
    ]
  }
}
```

### 5.2 Prueba de Invocación Operativa `tools/call` vía JSON-RPC:
**Entrada (stdin):**
```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "audit_pyme_cashflow", "arguments": {"input_csv": "data/ventas_diarias.csv", "output_md": "reports/cierre_diario_actual.md", "tolerance": 5.0}}}
```

**Respuesta recibida (stdout):**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Auditoría completada exitosamente.\n- Estado: BALANCE_OK\n- Transacciones analizadas: 20 (19 válidas, 1 en DLQ)\n- Duplicados detectados: 3\n- Total Ingresos: S/ 4,235.50\n- Total Egresos: S/ 455.00\n- Balance Neto Calculado: S/ 3,780.50\n- Custodia en Efectivo: S/ 620.00\n- Reporte Markdown generado en: reports\\cierre_diario_actual.md\n"
      }
    ]
  }
}
```

---

## 6. Criterios de Aceptación de la Fase 6
1. [x] Servidor MCP liviano implementado en `tools/mcp_server.py` sin dependencias externas.
2. [x] Manifiesto formal `.mcp/pyme_ops_mcp.json` para registro en clientes IA.
3. [x] Lanzador para clientes finales en Windows `deploy/run_audit.bat` validado y operativo.
4. [x] Smoke test de protocolo JSON-RPC (`tools/list` y `tools/call`) ejecutado con éxito.
5. [x] Documentación técnica de despliegue generada e interconectada en Obsidian.

---

## Navegación del Proyecto (Obsidian Graph)

| Nodo | Enlace |
| :--- | :--- |
| Inicio del Proyecto | [[README]] |
| ← Fase 5: Pruebas | [[05_fase_pruebas]] |
| → Fase 7: Mantenimiento | [[07_fase_mantenimiento]] |
| Runbook de Operaciones | [[sop_mantenimiento_operaciones]] |
| Fase de Implementación | [[04_fase_implementacion]] |
| SOP de Auditoría | [[sop_auditoria_caja]] |
| Evidencia de Reporte | [[cierre_diario_actual]] |
| Roles del Equipo | [[01_business_analyst]] · [[02_system_architect]] · [[03_software_engineer]] · [[04_qa_engineer]] |
