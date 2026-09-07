#!/usr/bin/env python3
"""
=============================================================================
PYME Ops Agent — Motor de Salud Operativa y Monitoreo SRE
=============================================================================
Módulo     : tools/maintenance_healthcheck.py
Fase SDLC  : 07 - Mantenimiento y Evolución
Autor      : SRE (Site Reliability Engineer) & Lead de Operaciones
Tecnología : Python estándar (json, sys, pathlib, datetime, decimal)
=============================================================================
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Definición de rutas críticas del sistema
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
TOOLS_DIR = ROOT_DIR / "tools"
SCHEMAS_DIR = DATA_DIR / "schemas"
DEPLOY_DIR = ROOT_DIR / "deploy"
TESTS_DIR = ROOT_DIR / "tests"

# Archivos críticos para validación de integridad
CRITICAL_ARTIFACTS: List[Tuple[str, Path, str]] = [
    ("Esquema JSON Formal", SCHEMAS_DIR / "transactions_schema.json", "Core Contract"),
    ("Motor de Auditoría", TOOLS_DIR / "audit_engine.py", "Core Engine"),
    ("Servidor MCP", TOOLS_DIR / "mcp_server.py", "Integration Server"),
    ("Lanzador Windows BAT", DEPLOY_DIR / "run_audit.bat", "Production Deploy"),
    ("Suite de Pruebas Unitarias", TESTS_DIR / "test_audit_engine.py", "QA Assurance"),
    ("Último Dictamen de Caja", REPORTS_DIR / "cierre_diario_actual.md", "Operational Report"),
    ("Log Dead Letter Queue (DLQ)", REPORTS_DIR / "dlq_anomalias.json", "Anomaly Quarantine"),
]

# Umbrales SRE
UMBRAL_CRITICO_ERROR_PCT = Decimal("10.0")  # > 10% = RED
UMBRAL_ADVERTENCIA_ERROR_PCT = Decimal("5.0")  # > 5% y <= 10% = YELLOW


def check_artifact_integrity() -> List[Dict[str, Any]]:
    """Verifica la existencia y tamaño de los artefactos críticos del sistema."""
    integrity_results: List[Dict[str, Any]] = []
    for nombre, path, categoria in CRITICAL_ARTIFACTS:
        existe = path.exists()
        size_bytes = path.stat().st_size if existe else 0
        status = "OK" if existe and size_bytes > 0 else "MISSING"
        integrity_results.append({
            "nombre": nombre,
            "categoria": categoria,
            "ruta": str(path.relative_to(ROOT_DIR)),
            "existe": existe,
            "size_bytes": size_bytes,
            "status": status,
        })
    return integrity_results


def inspect_dlq_metrics() -> Tuple[int, int, Decimal, List[Dict[str, Any]]]:
    """
    Inspecciona el archivo DLQ y el dataset de entrada para calcular
    la tasa de error y recopilar detalles de anomalías.
    """
    dlq_path = REPORTS_DIR / "dlq_anomalias.json"
    dataset_path = DATA_DIR / "ventas_diarias.csv"

    dlq_records: List[Dict[str, Any]] = []
    if dlq_path.exists():
        try:
            with open(dlq_path, "r", encoding="utf-8") as f:
                dlq_records = json.load(f)
        except Exception as e:
            sys.stderr.write(f"[WARN] Error leyendo DLQ: {e}\n")

    # Contar total de registros en el dataset de entrada
    total_input_records = 0
    if dataset_path.exists():
        try:
            with open(dataset_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                total_input_records = sum(1 for _ in reader)
        except Exception as e:
            sys.stderr.write(f"[WARN] Error leyendo dataset de entrada: {e}\n")

    total_dlq = len(dlq_records)
    total_processed = total_input_records if total_input_records > 0 else total_dlq
    total_valid = max(0, total_processed - total_dlq)

    # Cálculo de tasa de error
    if total_processed > 0:
        tasa_error = (Decimal(str(total_dlq)) / Decimal(str(total_processed))) * Decimal("100.0")
        tasa_error = tasa_error.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        tasa_error = Decimal("0.00")

    return total_processed, total_dlq, tasa_error, dlq_records


def determine_health_status(
    integrity_results: List[Dict[str, Any]],
    tasa_error: Decimal,
) -> Tuple[str, str, str]:
    """
    Determina el estado global de salud:
    - RED: Si falta algún archivo crítico esencial o la tasa de error > 10%
    - YELLOW: Si la tasa de error está entre 5% y 10%
    - GREEN: Sistema íntegro y tasa de error <= 5%
    """
    # Verificar si faltan artefactos esenciales
    missing_essentials = any(
        r["status"] == "MISSING" and r["categoria"] in ["Core Contract", "Core Engine", "Integration Server"]
        for r in integrity_results
    )

    if missing_essentials or tasa_error > UMBRAL_CRITICO_ERROR_PCT:
        return "RED", "CRITICAL", "[CRITICAL] Estado Critico: Se requiere intervencion inmediata de SRE."
    elif tasa_error > UMBRAL_ADVERTENCIA_ERROR_PCT:
        return "YELLOW", "WARNING", "[WARNING] Advertencia: Tasa de anomalias por encima del umbral preventivo (5%)."
    else:
        return "GREEN", "HEALTHY", "[OK] Sistema Saludable: Operatividad optima y tolerancias bajo control."


def generate_markdown_report(
    health_color: str,
    health_label: str,
    health_desc: str,
    total_processed: int,
    total_dlq: int,
    tasa_error: Decimal,
    integrity_results: List[Dict[str, Any]],
    dlq_records: List[Dict[str, Any]],
    output_file: Path,
) -> None:
    """Genera el documento formal reports/system_health_status.md estructurado para Obsidian."""
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    lines: List[str] = [
        "---",
        f'title: "Informe de Salud Operativa y Monitoreo SRE — {fecha_hoy}"',
        f"fecha_monitoreo: {fecha_hoy}",
        'proyecto: "PYME Ops Agent"',
        'responsable: "SRE & Lead de Operaciones"',
        f"estado_salud: {health_label}",
        f"color_diagnostico: {health_color}",
        "tags:",
        "  - salud-sistema",
        "  - sre",
        "  - monitoreo",
        "  - mantenimiento",
        "---",
        "",
        f"# 🏥 Informe de Salud Operativa y Monitoreo SRE — {fecha_hoy}",
        "",
        f"> **Diagnóstico Global:** **[{health_color}] {health_label}**  ",
        f"> **Descripción:** {health_desc}  ",
        f"> **Última Verificación:** `{timestamp_str}`  ",
        f"> **Agente Responsable:** SRE & Lead de Operaciones (`[[02_system_architect]]` / Lead DevOps)",
        "",
        "---",
        "",
        "## 1. Indicadores Clave de Salud Operativa (KPIs SRE)",
        "",
        "| Métrica Operativa | Valor Registrado | Umbral Tolerable | Evaluación |",
        "| :--- | :---: | :---: | :---: |",
        f"| **Volumen Total Procesado** | `{total_processed}` registros | N/A | Informativo |",
        f"| **Transacciones Válidas** | `{total_processed - total_dlq}` registros | N/A | Conforme |",
        f"| **Anomalías en Cuarentena (DLQ)** | `{total_dlq}` registros | 0 - 2 | Controlado |",
        f"| **Tasa de Error DLQ** | **`{tasa_error}%`** | Max 10.0% | {'✅ Aprobado' if tasa_error <= 10.0 else '🚨 Crítico'} |",
        f"| **Integridad de Artefactos Críticos** | `{sum(1 for r in integrity_results if r['status'] == 'OK')}/{len(integrity_results)}` verificados | 100% | {'✅ Óptimo' if all(r['status'] == 'OK' for r in integrity_results) else '⚠️ Incompleto'} |",
        "",
        "---",
        "",
        "## 2. Matriz de Integridad de Componentes y Artefactos",
        "",
        "| Componente / Archivo | Categoría | Ruta Relativa | Tamaño (Bytes) | Estado |",
        "| :--- | :--- | :--- | :---: | :---: |",
    ]

    for r in integrity_results:
        estado_icon = "🟢 OK" if r["status"] == "OK" else "🔴 FALTA"
        lines.append(f"| **{r['nombre']}** | {r['categoria']} | `{r['ruta']}` | {r['size_bytes']:,} B | {estado_icon} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Auditoría del Dead Letter Queue (DLQ)",
        "",
    ])

    if dlq_records:
        lines.extend([
            f"> [!NOTE]",
            f"> Se registran `{len(dlq_records)}` anomalía(s) en cuarentena en `reports/dlq_anomalias.json`. La tasa de rechazo actual es de **{tasa_error}%**, dentro de los márgenes admisibles.",
            "",
            "| ID Registro DLQ | Campo Incriminado | Motivo del Rechazo | Timestamp Cuarentena |",
            "| :--- | :--- | :--- | :--- |",
        ])
        for dlq in dlq_records:
            dlq_id = dlq.get("dlq_id", "N/A")
            campo = dlq.get("campo_incriminado", "N/A")
            motivo = dlq.get("motivo_rechazo", "N/A")
            ts = dlq.get("timestamp_registro", "N/A")
            lines.append(f"| `{dlq_id}` | `{campo}` | {motivo} | `{ts}` |")
    else:
        lines.extend([
            "> [!NOTE]",
            "> No se registran anomalías en la cola DLQ. Cero rechazos reportados.",
            "",
        ])

    lines.extend([
        "",
        "---",
        "",
        "## 4. Recomendaciones de Mantenimiento Preventivo",
        "",
        "1. **Monitoreo Continuo:** Ejecutar `tools/maintenance_healthcheck.py` al cierre de cada turno operativo.",
        "2. **Rotación de Reportes:** Archivar mensual de dictámenes en `reports/archive/` según lo estipulado en [[sop_mantenimiento_operaciones]].",
        "3. **Trazabilidad en Origen:** Validar con el equipo de ventas los motivos de omisión de campos obligatorios en el POS antes de la exportación.",
        "",
        "---",
        "",
        "## Navegación y Trazabilidad (Obsidian Graph)",
        "",
        "| Referencia | Enlace |",
        "| :--- | :--- |",
        "| Inicio del Proyecto | [[README]] |",
        "| Documento de Cierre SDLC | [[07_fase_mantenimiento]] |",
        "| Runbook Operativo de Mantenimiento | [[sop_mantenimiento_operaciones]] |",
        "| Dictamen Diario Auditado | [[cierre_diario_actual]] |",
        "| Fase de Despliegue | [[06_fase_despliegue]] |",
        "| Fase de Pruebas | [[05_fase_pruebas]] |",
        "",
        "*Reporte generado automáticamente por `tools/maintenance_healthcheck.py` — SRE Ops Engine v1.0.0*",
    ])

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    print("=" * 65)
    print("  PYME Ops Agent — Healthcheck y Diagnóstico Operativo SRE")
    print("=" * 65)

    # 1. Verificar integridad de archivos
    print("\n[1/3] Auditando integridad física de componentes...")
    integrity_results = check_artifact_integrity()
    ok_count = sum(1 for r in integrity_results if r["status"] == "OK")
    print(f"      Componentes verificados: {ok_count}/{len(integrity_results)} [OK]")

    # 2. Analizar métricas de DLQ
    print("\n[2/3] Inspeccionando anomalías y tasa de rechazo DLQ...")
    total_processed, total_dlq, tasa_error, dlq_records = inspect_dlq_metrics()
    print(f"      Total transacciones evaluadas: {total_processed}")
    print(f"      Registros en DLQ             : {total_dlq}")
    print(f"      Tasa de error observada      : {tasa_error}%")

    # 3. Determinar diagnóstico y emitir informe
    print("\n[3/3] Evaluando diagnóstico global y generando informe...")
    health_color, health_label, health_desc = determine_health_status(integrity_results, tasa_error)
    print(f"      Diagnóstico: [{health_color}] {health_label}")
    print(f"      {health_desc}")

    out_report = REPORTS_DIR / "system_health_status.md"
    generate_markdown_report(
        health_color=health_color,
        health_label=health_label,
        health_desc=health_desc,
        total_processed=total_processed,
        total_dlq=total_dlq,
        tasa_error=tasa_error,
        integrity_results=integrity_results,
        dlq_records=dlq_records,
        output_file=out_report,
    )
    print(f"\n      [OK] Informe de salud generado en: {out_report.relative_to(ROOT_DIR)}")
    print("=" * 65 + "\n")

    return 0 if health_color in ["GREEN", "YELLOW"] else 1


if __name__ == "__main__":
    sys.exit(main())
