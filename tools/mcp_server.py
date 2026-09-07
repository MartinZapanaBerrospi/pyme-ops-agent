#!/usr/bin/env python3
"""
=============================================================================
PYME Ops Agent — Servidor MCP (Model Context Protocol)
=============================================================================
Módulo     : tools/mcp_server.py
Fase SDLC  : 06 - Despliegue y Puesta en Marcha
Autor      : Lead DevOps & Software Architect
Estándar   : MCP Specification (JSON-RPC 2.0 sobre stdio)
Tecnología : Python Estándar (json, sys, pathlib, decimal, datetime)
=============================================================================
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

# Importar el motor de auditoría determinista
try:
    from tools.audit_engine import (
        AuditEngine,
        DataIngestion,
        EstadoAuditoria,
        ReportGenerator,
        SchemaValidator,
    )
except ImportError:
    # Soporte cuando se ejecuta directamente desde la raíz del proyecto
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.audit_engine import (
        AuditEngine,
        DataIngestion,
        EstadoAuditoria,
        ReportGenerator,
        SchemaValidator,
    )


# Metadatos del Servidor MCP
SERVER_NAME = "pyme-ops-mcp"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"

# Catálogo formal de tools expuestas según especificación MCP
TOOL_AUDIT_PYME_CASHFLOW: Dict[str, Any] = {
    "name": "audit_pyme_cashflow",
    "description": (
        "Audita transacciones de ventas diarias de una PYME, detecta cobros "
        "duplicados en ventana de tiempo y genera reporte financiero en Markdown."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "input_csv": {
                "type": "string",
                "description": "Ruta del archivo CSV de transacciones a auditar.",
            },
            "output_md": {
                "type": "string",
                "description": "Ruta destino para el reporte Markdown generado.",
                "default": "reports/cierre_diario_actual.md",
            },
            "tolerance": {
                "type": "number",
                "description": "Umbral de tolerancia de descuadre porcentual (0 - 100).",
                "default": 5.0,
            },
            "declared": {
                "type": "number",
                "description": "Monto declarado en arqueo físico de caja (opcional).",
            },
        },
        "required": ["input_csv"],
    },
}


def send_response(response: Dict[str, Any]) -> None:
    """Envía un mensaje JSON-RPC formateado a stdout asegurando flush inmediato."""
    payload = json.dumps(response, ensure_ascii=False)
    sys.stdout.write(payload + "\n")
    sys.stdout.flush()


def send_error(req_id: Any, code: int, message: str, data: Any = None) -> None:
    """Envía una respuesta de error JSON-RPC estándar."""
    error_obj: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error_obj["data"] = data
    send_response({
        "jsonrpc": "2.0",
        "id": req_id,
        "error": error_obj,
    })


def execute_audit_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta el motor de auditoría con los argumentos proporcionados por el cliente MCP.
    Retorna el resultado en el formato de contenido estándar de MCP.
    """
    input_csv_str = arguments.get("input_csv")
    if not input_csv_str:
        return {
            "isError": True,
            "content": [{"type": "text", "text": "Error: El parámetro 'input_csv' es obligatorio."}],
        }

    input_csv = Path(input_csv_str)
    schema_path = Path("data/schemas/transactions_schema.json")
    output_md_str = arguments.get("output_md", "reports/cierre_diario_actual.md")
    output_md = Path(output_md_str)
    tolerance = Decimal(str(arguments.get("tolerance", 5.0)))
    declared_raw = arguments.get("declared")
    declared = Decimal(str(declared_raw)) if declared_raw is not None else None

    # Validaciones de rutas
    if not input_csv.exists():
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Error: No se encontró el archivo de entrada '{input_csv}'."}],
        }

    if not schema_path.exists():
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Error: No se encontró el esquema formal '{schema_path}'."}],
        }

    try:
        # 1. Cargar datos
        records_raw = DataIngestion.load(input_csv)

        # 2. Validar esquema y separar DLQ
        validator = SchemaValidator(schema_path)
        transactions, dlq_records = validator.validate_batch(records_raw)

        if not transactions:
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": "Error: Cero registros válidos tras la validación contra el esquema.",
                    }
                ],
            }

        # 3. Ejecutar auditoría determinista
        result = AuditEngine.run_full_audit(
            transactions=transactions,
            monto_declarado=declared,
            tolerancia_pct=tolerance,
            fecha_auditoria=datetime.now(),
            ruta_reporte=output_md,
            dlq_records=dlq_records,
        )

        # 4. Generar reporte Markdown y guardar en disco
        md_content = ReportGenerator.generate(result)
        ReportGenerator.write_to_disk(md_content, output_md)

        # Serializar DLQ si hubieron anomalías
        if dlq_records:
            dlq_path = Path("reports/dlq_anomalias.json")
            from tools.audit_engine import _serialize_dlq
            _serialize_dlq(dlq_records, dlq_path)

        resumen_texto = (
            f"Auditoría completada exitosamente.\n"
            f"- Estado: {result.estado.value}\n"
            f"- Transacciones analizadas: {result.total_registros_entrada} "
            f"({result.total_registros_validos} válidas, {result.total_registros_dlq} en DLQ)\n"
            f"- Duplicados detectados: {len(result.duplicados)}\n"
            f"- Total Ingresos: S/ {result.balance.total_ingresos:,.2f}\n"
            f"- Total Egresos: S/ {result.balance.total_egresos:,.2f}\n"
            f"- Balance Neto Calculado: S/ {result.balance.balance_neto:,.2f}\n"
            f"- Custodia en Efectivo: S/ {result.balance.custodia_efectivo:,.2f}\n"
            f"- Reporte Markdown generado en: {output_md}\n"
        )
        if result.discrepancia_pct is not None:
            resumen_texto += f"- Discrepancia con arqueo físico: {result.discrepancia_pct}%\n"

        return {
            "content": [
                {
                    "type": "text",
                    "text": resumen_texto,
                }
            ]
        }

    except Exception as exc:
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Excepción durante la auditoría: {exc}"}],
        }


def handle_request(line: str) -> None:
    """Procesa una línea de comando entrante bajo el protocolo JSON-RPC 2.0."""
    line = line.strip()
    if not line:
        return

    try:
        req = json.loads(line)
    except json.JSONDecodeError:
        send_error(None, -32700, "Parse error: Formato JSON inválido.")
        return

    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    # Manejo de notificaciones (sin id requerido)
    if method == "notifications/initialized":
        # Handshake completado por el cliente
        return

    # Si no tiene id y no es notificación conocida, ignorar
    if req_id is None and not method:
        return

    # 1. Handshake MCP: initialize
    if method == "initialize":
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {
                        "listChanged": False
                    }
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            },
        })
        return

    # 2. Ping
    if method == "ping":
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {},
        })
        return

    # 3. Listar herramientas: tools/list
    if method == "tools/list":
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [TOOL_AUDIT_PYME_CASHFLOW],
            },
        })
        return

    # 4. Invocar herramienta: tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "audit_pyme_cashflow":
            call_result = execute_audit_tool(arguments)
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": call_result,
            })
            return
        else:
            send_error(req_id, -32601, f"Tool '{tool_name}' no encontrada en este servidor.")
            return

    # Método no soportado
    send_error(req_id, -32601, f"Método '{method}' no soportado por este servidor MCP.")


def main() -> None:
    """Bucle principal de escucha en stdio."""
    # Redirigir logs no deseados a stderr para mantener stdout puramente JSON-RPC
    sys.stderr.write(f"[{SERVER_NAME}] Servidor MCP iniciado v{SERVER_VERSION}. Escuchando en stdio...\n")
    sys.stderr.flush()

    for line in sys.stdin:
        handle_request(line)


if __name__ == "__main__":
    main()
