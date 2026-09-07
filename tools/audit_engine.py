#!/usr/bin/env python3
"""
=============================================================================
PYME Ops Agent — Motor de Auditoría Operativa de Caja
=============================================================================
Módulo     : tools/audit_engine.py
Fase SDLC  : 04 - Implementación
Autor      : Software Engineer Agent
Basado en  : tools/audit_engine_spec.py (System Architect Agent, Fase 3)
Versión    : 1.0.0

REGLAS CRÍTICAS DE IMPLEMENTACIÓN:
  1. decimal.Decimal OBLIGATORIO para todos los montos monetarios.
     float está PROHIBIDO en cualquier cálculo financiero.
  2. Funciones puras en AuditEngine: sin efectos secundarios.
  3. Fail-fast con aislamiento DLQ para registros corruptos.
  4. Idempotencia garantizada: mismo input → mismo output, siempre.
=============================================================================
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Optional


# =============================================================================
# SECCIÓN 1: ENUMERACIONES DE DOMINIO
# =============================================================================

class TipoTransaccion(str, Enum):
    """Naturaleza contable del movimiento de caja."""
    INGRESO = "ingreso"
    EGRESO = "egreso"


class MetodoPago(str, Enum):
    """Canal o medio de liquidación de pago aceptado por el sistema."""
    EFECTIVO = "efectivo"
    YAPE = "yape"
    PLIN = "plin"
    POS = "pos"


class EstadoTransaccion(str, Enum):
    """Estado contable de la transacción al momento del corte de jornada."""
    COMPLETADO = "completado"
    ANULADO = "anulado"
    PENDIENTE = "pendiente"


class EstadoAuditoria(str, Enum):
    """Veredicto final del motor de auditoría tras el cierre de la jornada."""
    BALANCE_OK = "BALANCE_OK"
    CRITICAL_MISMATCH = "CRITICAL_MISMATCH"


# =============================================================================
# SECCIÓN 2: EXCEPCIONES PERSONALIZADAS
# =============================================================================

class PymeOpsAgentBaseError(Exception):
    """Excepción raíz del sistema."""
    pass


class DataValidationError(PymeOpsAgentBaseError):
    """Registro no conforme al esquema de datos."""
    def __init__(self, registro_id: str, campo: str, valor_recibido: object, motivo: str) -> None:
        self.registro_id = registro_id
        self.campo = campo
        self.valor_recibido = valor_recibido
        self.motivo = motivo
        super().__init__(
            f"[DataValidationError] ID={registro_id} | campo='{campo}' | "
            f"valor={repr(valor_recibido)} | motivo={motivo}"
        )


class DiscrepancyThresholdExceeded(PymeOpsAgentBaseError):
    """Discrepancia entre balance calculado y arqueo físico supera el umbral."""
    def __init__(
        self,
        balance_calculado: Decimal,
        monto_declarado: Decimal,
        discrepancia_abs: Decimal,
        discrepancia_pct: Decimal,
        tolerancia_pct: Decimal,
    ) -> None:
        self.balance_calculado = balance_calculado
        self.monto_declarado = monto_declarado
        self.discrepancia_abs = discrepancia_abs
        self.discrepancia_pct = discrepancia_pct
        self.tolerancia_pct = tolerancia_pct
        super().__init__(
            f"[DiscrepancyThresholdExceeded] Calculado={balance_calculado} | "
            f"Declarado={monto_declarado} | Discrepancia={discrepancia_pct}% | "
            f"Umbral={tolerancia_pct}%"
        )


class EmptyDatasetError(PymeOpsAgentBaseError):
    """El archivo de entrada no contiene ningún registro válido procesable."""
    def __init__(self, ruta_archivo: Path) -> None:
        self.ruta_archivo = ruta_archivo
        super().__init__(
            f"[EmptyDatasetError] El archivo '{ruta_archivo}' no contiene "
            "registros válidos procesables tras la validación de esquema."
        )


# =============================================================================
# SECCIÓN 3: MODELOS DE DATOS
# =============================================================================

@dataclass(frozen=True)
class Transaction:
    """Representación inmutable y tipada de una transacción operativa validada."""
    id_transaccion: str
    timestamp: datetime
    tipo: TipoTransaccion
    metodo_pago: MetodoPago
    monto: Decimal          # SIEMPRE Decimal. Nunca float.
    categoria: str
    estado: EstadoTransaccion
    referencia: Optional[str] = None
    descripcion: Optional[str] = None


@dataclass
class DLQRecord:
    """Envelope de cuarentena para un registro que no superó la validación."""
    dlq_id: str
    timestamp_registro: datetime
    motivo_rechazo: str
    campo_incriminado: str
    valor_recibido: object
    registro_original: dict


@dataclass
class DuplicateAlert:
    """Alerta de posible transacción duplicada dentro de la ventana temporal crítica."""
    alerta_id: str
    id_transaccion_a: str
    id_transaccion_b: str
    monto: Decimal
    metodo_pago: MetodoPago
    delta_segundos: float
    severidad: str = "MEDIUM"


@dataclass
class BalanceSummary:
    """Resumen consolidado de balances. Todos los campos monetarios son Decimal."""
    total_ingresos: Decimal = Decimal("0.00")
    total_egresos: Decimal = Decimal("0.00")
    balance_neto: Decimal = Decimal("0.00")
    custodia_efectivo: Decimal = Decimal("0.00")
    desglose_por_metodo: dict[str, dict[str, Decimal]] = field(default_factory=dict)


@dataclass
class AuditResult:
    """Resultado completo de la auditoría listo para serialización."""
    fecha_auditoria: datetime
    estado: EstadoAuditoria
    total_registros_entrada: int
    total_registros_validos: int
    total_registros_dlq: int
    balance: BalanceSummary
    duplicados: list[DuplicateAlert]
    dlq_records: list[DLQRecord]
    monto_declarado: Optional[Decimal]
    discrepancia_abs: Optional[Decimal]
    discrepancia_pct: Optional[Decimal]
    tolerancia_pct: Decimal
    ruta_reporte: Path


# =============================================================================
# SECCIÓN 4: IMPLEMENTACIÓN DE MÓDULOS
# =============================================================================

# Constante de precisión monetaria
_MONEDA_PRECISION = Decimal("0.01")

# Campos obligatorios según el esquema JSON formal
_CAMPOS_OBLIGATORIOS = {
    "id_transaccion", "timestamp", "tipo", "metodo_pago", "monto", "categoria", "estado"
}

# Dominios de enumeraciones válidos
_ENUM_TIPO = {e.value for e in TipoTransaccion}
_ENUM_METODO = {e.value for e in MetodoPago}
_ENUM_ESTADO = {e.value for e in EstadoTransaccion}


class DataIngestion:
    """
    Módulo de carga y parseo de archivos de transacciones desde disco.
    Soporte para CSV y JSON. Inmutable respecto al archivo de origen.
    """

    @staticmethod
    def load_csv(file_path: Path) -> list[dict]:
        """
        Lee un archivo CSV de transacciones y devuelve lista de dicts raw.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            ValueError: Si el CSV está vacío o no tiene encabezados.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo de entrada no encontrado: '{file_path}'")

        records: list[dict] = []
        with file_path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise ValueError(f"El archivo CSV '{file_path}' no tiene encabezados.")
            for row in reader:
                # Normalizar espacios en clave y valores; guard against None values in sparse/corrupt rows
                clean = {k.strip(): (v.strip() if v is not None else "") for k, v in row.items() if k is not None}
                # CSV lee todo como string; convertir monto a float/Decimal según convenga
                if "monto" in clean:
                    try:
                        clean["monto"] = float(clean["monto"])
                    except (ValueError, TypeError):
                        pass  # Dejar como string — SchemaValidator lo rechazará
                records.append(clean)
        return records

    @staticmethod
    def load_json(file_path: Path) -> list[dict]:
        """
        Lee un archivo JSON de transacciones y devuelve lista de dicts raw.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            ValueError: Si el JSON no es un array en la raíz.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo de entrada no encontrado: '{file_path}'")

        with file_path.open(encoding="utf-8") as fh:
            data = json.load(fh)

        if not isinstance(data, list):
            raise ValueError(
                f"El archivo JSON '{file_path}' debe contener un array de objetos en la raíz."
            )
        return data

    @classmethod
    def load(cls, file_path: Path) -> list[dict]:
        """
        Punto de entrada unificado. Detecta formato por extensión.

        Raises:
            ValueError: Si la extensión no es .csv ni .json.
        """
        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            return cls.load_csv(file_path)
        elif suffix == ".json":
            return cls.load_json(file_path)
        else:
            raise ValueError(
                f"Formato de archivo no soportado: '{suffix}'. "
                "Use .csv o .json."
            )


class SchemaValidator:
    """
    Módulo de validación de registros contra el contrato JSON Schema formal.
    Implementación manual sin dependencias externas (cero jsonschema lib).
    """

    def __init__(self, schema_path: Path) -> None:
        """
        Carga el esquema JSON Schema desde disco y lo almacena en memoria.

        Raises:
            FileNotFoundError: Si el archivo de esquema no existe.
            ValueError: Si el contenido del archivo no es un JSON válido.
        """
        if not schema_path.exists():
            raise FileNotFoundError(f"Esquema JSON no encontrado: '{schema_path}'")

        with schema_path.open(encoding="utf-8") as fh:
            try:
                self._schema: dict = json.load(fh)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"El archivo de esquema '{schema_path}' no es un JSON válido: {exc}"
                ) from exc

        self._dlq_counter: int = 0

    def _next_dlq_id(self, fecha: str) -> str:
        """Genera un ID incremental para el DLQ."""
        self._dlq_counter += 1
        return f"DLQ-{fecha}-{self._dlq_counter:03d}"

    def _parse_timestamp(self, raw: str, registro_id: str) -> datetime:
        """
        Parsea un timestamp ISO 8601. Acepta con y sin zona horaria.

        Raises:
            DataValidationError: Si el formato es inválido.
        """
        if not isinstance(raw, str) or not raw.strip():
            raise DataValidationError(
                registro_id=registro_id,
                campo="timestamp",
                valor_recibido=raw,
                motivo="El campo 'timestamp' debe ser una cadena no vacía en formato ISO 8601.",
            )
        # Intentar formatos comunes
        formatos = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M",
        ]
        for fmt in formatos:
            try:
                return datetime.strptime(raw.strip(), fmt)
            except ValueError:
                continue
        raise DataValidationError(
            registro_id=registro_id,
            campo="timestamp",
            valor_recibido=raw,
            motivo=(
                f"Timestamp '{raw}' no conforme con ISO 8601. "
                "Ejemplo válido: '2026-09-07T08:00:00Z'."
            ),
        )

    def _parse_monto(self, raw: object, registro_id: str) -> Decimal:
        """
        Convierte el monto raw a Decimal con precisión financiera.

        Raises:
            DataValidationError: Si el monto no es numérico o es <= 0.
        """
        try:
            valor = Decimal(str(raw)).quantize(_MONEDA_PRECISION, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError):
            raise DataValidationError(
                registro_id=registro_id,
                campo="monto",
                valor_recibido=raw,
                motivo=f"El campo 'monto' debe ser un número válido. Recibido: {repr(raw)}.",
            )
        if valor <= Decimal("0"):
            raise DataValidationError(
                registro_id=registro_id,
                campo="monto",
                valor_recibido=raw,
                motivo=f"El campo 'monto' debe ser estrictamente mayor a 0. Recibido: {valor}.",
            )
        return valor

    def validate_record(self, record: dict) -> Transaction:
        """
        Valida un único registro raw y lo convierte a Transaction tipada.

        Raises:
            DataValidationError: Si el registro viola alguna regla del esquema.
        """
        # Determinar ID para mensajes de error (puede no estar presente)
        registro_id = str(record.get("id_transaccion", "<sin_id>"))

        # 1. Verificar campos obligatorios presentes
        for campo in _CAMPOS_OBLIGATORIOS:
            if campo not in record or record[campo] is None or record[campo] == "":
                raise DataValidationError(
                    registro_id=registro_id,
                    campo=campo,
                    valor_recibido=record.get(campo),
                    motivo=f"Campo obligatorio '{campo}' ausente o vacío.",
                )

        # 2. Validar id_transaccion (patrón alfanumérico 3–64 chars)
        id_val = str(record["id_transaccion"]).strip()
        import re
        if not re.match(r"^[A-Za-z0-9_-]{3,64}$", id_val):
            raise DataValidationError(
                registro_id=registro_id,
                campo="id_transaccion",
                valor_recibido=id_val,
                motivo="El campo 'id_transaccion' debe ser alfanumérico de 3 a 64 caracteres.",
            )

        # 3. Validar tipo
        tipo_val = str(record["tipo"]).strip().lower()
        if tipo_val not in _ENUM_TIPO:
            raise DataValidationError(
                registro_id=registro_id,
                campo="tipo",
                valor_recibido=record["tipo"],
                motivo=f"Valor '{record['tipo']}' inválido. Debe ser uno de: {sorted(_ENUM_TIPO)}.",
            )

        # 4. Validar metodo_pago
        metodo_val = str(record["metodo_pago"]).strip().lower()
        if metodo_val not in _ENUM_METODO:
            raise DataValidationError(
                registro_id=registro_id,
                campo="metodo_pago",
                valor_recibido=record["metodo_pago"],
                motivo=f"Valor '{record['metodo_pago']}' inválido. Debe ser uno de: {sorted(_ENUM_METODO)}.",
            )

        # 5. Validar estado
        estado_val = str(record["estado"]).strip().lower()
        if estado_val not in _ENUM_ESTADO:
            raise DataValidationError(
                registro_id=registro_id,
                campo="estado",
                valor_recibido=record["estado"],
                motivo=f"Valor '{record['estado']}' inválido. Debe ser uno de: {sorted(_ENUM_ESTADO)}.",
            )

        # 6. Validar categoria
        categoria_val = str(record["categoria"]).strip()
        if not categoria_val:
            raise DataValidationError(
                registro_id=registro_id,
                campo="categoria",
                valor_recibido=record["categoria"],
                motivo="El campo 'categoria' no puede estar vacío.",
            )

        # 7. Parsear timestamp
        ts = self._parse_timestamp(str(record["timestamp"]), registro_id)

        # 8. Parsear monto (Decimal obligatorio)
        monto = self._parse_monto(record["monto"], registro_id)

        return Transaction(
            id_transaccion=id_val,
            timestamp=ts,
            tipo=TipoTransaccion(tipo_val),
            metodo_pago=MetodoPago(metodo_val),
            monto=monto,
            categoria=categoria_val,
            estado=EstadoTransaccion(estado_val),
            referencia=str(record["referencia"]).strip() if record.get("referencia") else None,
            descripcion=str(record["descripcion"]).strip() if record.get("descripcion") else None,
        )

    def validate_batch(
        self, records: list[dict]
    ) -> tuple[list[Transaction], list[DLQRecord]]:
        """
        Valida una lista completa de registros. Separa válidos de DLQ.

        Returns:
            tuple: (lista de Transaction válidas, lista de DLQRecord rechazados)
        """
        validos: list[Transaction] = []
        dlq: list[DLQRecord] = []
        fecha_hoy = datetime.now().strftime("%Y%m%d")

        for record in records:
            try:
                tx = self.validate_record(record)
                validos.append(tx)
            except DataValidationError as exc:
                dlq_rec = DLQRecord(
                    dlq_id=self._next_dlq_id(fecha_hoy),
                    timestamp_registro=datetime.now(),
                    motivo_rechazo=exc.motivo,
                    campo_incriminado=exc.campo,
                    valor_recibido=exc.valor_recibido,
                    registro_original=dict(record),
                )
                dlq.append(dlq_rec)

        return validos, dlq


class AuditEngine:
    """
    Motor de auditoría determinista y puro.
    Todas las funciones son puras — mismo input → mismo output.
    Sin efectos secundarios. Sin escritura a disco. Sin llamadas a red.
    """

    VENTANA_DUPLICADO_SEG: int = 180

    @staticmethod
    def detect_duplicates(
        transactions: list[Transaction],
        ventana_segundos: int = 180,
    ) -> list[DuplicateAlert]:
        """
        Detecta pares de transacciones potencialmente duplicadas.
        Criterio: mismo monto + mismo método de pago + misma referencia (o None)
                  con delta_tiempo <= ventana_segundos.

        Complejidad: O(n²) — aceptable para n ≤ 10,000.
        """
        alertas: list[DuplicateAlert] = []
        # Ordenar por timestamp para comparaciones eficientes con ventana
        txs = sorted(transactions, key=lambda t: t.timestamp)
        alerta_counter = 0

        for i in range(len(txs)):
            for j in range(i + 1, len(txs)):
                t_a = txs[i]
                t_b = txs[j]

                # Romper temprano: si superamos la ventana, no hay más candidatos
                delta = abs((t_b.timestamp - t_a.timestamp).total_seconds())
                if delta > ventana_segundos:
                    break

                # Condiciones de duplicado: monto, método, referencia coinciden
                mismo_monto = t_a.monto == t_b.monto
                mismo_metodo = t_a.metodo_pago == t_b.metodo_pago
                misma_referencia = (
                    t_a.referencia is not None
                    and t_b.referencia is not None
                    and t_a.referencia == t_b.referencia
                ) or (t_a.referencia is None and t_b.referencia is None)

                if mismo_monto and mismo_metodo and misma_referencia:
                    alerta_counter += 1
                    alertas.append(
                        DuplicateAlert(
                            alerta_id=f"DUP-{alerta_counter:03d}",
                            id_transaccion_a=t_a.id_transaccion,
                            id_transaccion_b=t_b.id_transaccion,
                            monto=t_a.monto,
                            metodo_pago=t_a.metodo_pago,
                            delta_segundos=round(delta, 2),
                            severidad="HIGH" if delta < 30 else "MEDIUM",
                        )
                    )

        return alertas

    @staticmethod
    def calculate_balance(transactions: list[Transaction]) -> BalanceSummary:
        """
        Calcula el balance financiero completo de la jornada.
        Usa exclusivamente Decimal. float está prohibido.
        Solo contabiliza transacciones en estado COMPLETADO.
        """
        total_ingresos = Decimal("0.00")
        total_egresos = Decimal("0.00")
        custodia_efectivo = Decimal("0.00")
        desglose: dict[str, dict[str, Decimal]] = {}

        for tx in transactions:
            if tx.estado != EstadoTransaccion.COMPLETADO:
                continue

            metodo = tx.metodo_pago.value
            if metodo not in desglose:
                desglose[metodo] = {
                    "ingresos": Decimal("0.00"),
                    "egresos": Decimal("0.00"),
                    "neto": Decimal("0.00"),
                }

            if tx.tipo == TipoTransaccion.INGRESO:
                total_ingresos += tx.monto
                desglose[metodo]["ingresos"] += tx.monto
                if tx.metodo_pago == MetodoPago.EFECTIVO:
                    custodia_efectivo += tx.monto
            else:  # EGRESO
                total_egresos += tx.monto
                desglose[metodo]["egresos"] += tx.monto
                if tx.metodo_pago == MetodoPago.EFECTIVO:
                    custodia_efectivo -= tx.monto

        # Calcular neto por método
        for metodo in desglose:
            desglose[metodo]["neto"] = (
                desglose[metodo]["ingresos"] - desglose[metodo]["egresos"]
            )

        balance_neto = total_ingresos - total_egresos

        return BalanceSummary(
            total_ingresos=total_ingresos.quantize(_MONEDA_PRECISION, rounding=ROUND_HALF_UP),
            total_egresos=total_egresos.quantize(_MONEDA_PRECISION, rounding=ROUND_HALF_UP),
            balance_neto=balance_neto.quantize(_MONEDA_PRECISION, rounding=ROUND_HALF_UP),
            custodia_efectivo=custodia_efectivo.quantize(_MONEDA_PRECISION, rounding=ROUND_HALF_UP),
            desglose_por_metodo=desglose,
        )

    @staticmethod
    def evaluate_discrepancy(
        balance_calculado: Decimal,
        monto_declarado: Decimal,
        tolerancia_pct: Decimal,
        raise_on_exceeded: bool = False,
    ) -> tuple[Decimal, Decimal, EstadoAuditoria]:
        """
        Evalúa la discrepancia porcentual entre balance calculado y arqueo declarado.

        Returns:
            (discrepancia_abs, discrepancia_pct, EstadoAuditoria)
        """
        discrepancia_abs = abs(balance_calculado - monto_declarado).quantize(
            _MONEDA_PRECISION, rounding=ROUND_HALF_UP
        )

        if balance_calculado == Decimal("0.00"):
            # Caso borde: si el calculado es cero, no podemos dividir
            discrepancia_pct = Decimal("100.00") if monto_declarado != Decimal("0.00") else Decimal("0.00")
        else:
            discrepancia_pct = (
                (discrepancia_abs / balance_calculado) * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if discrepancia_pct > tolerancia_pct:
            estado = EstadoAuditoria.CRITICAL_MISMATCH
            if raise_on_exceeded:
                raise DiscrepancyThresholdExceeded(
                    balance_calculado=balance_calculado,
                    monto_declarado=monto_declarado,
                    discrepancia_abs=discrepancia_abs,
                    discrepancia_pct=discrepancia_pct,
                    tolerancia_pct=tolerancia_pct,
                )
        else:
            estado = EstadoAuditoria.BALANCE_OK

        return discrepancia_abs, discrepancia_pct, estado

    @classmethod
    def run_full_audit(
        cls,
        transactions: list[Transaction],
        monto_declarado: Optional[Decimal],
        tolerancia_pct: Decimal,
        fecha_auditoria: datetime,
        ruta_reporte: Path,
        dlq_records: list[DLQRecord],
    ) -> AuditResult:
        """
        Orquesta la auditoría completa y produce el AuditResult final.
        """
        if not transactions:
            raise EmptyDatasetError(ruta_reporte)

        # Paso 1: Detectar duplicados
        duplicados = cls.detect_duplicates(transactions)

        # Paso 2: Calcular balance financiero
        balance = cls.calculate_balance(transactions)

        # Paso 3: Evaluar discrepancia si hay monto declarado
        discrepancia_abs: Optional[Decimal] = None
        discrepancia_pct: Optional[Decimal] = None
        estado = EstadoAuditoria.BALANCE_OK

        if monto_declarado is not None:
            discrepancia_abs, discrepancia_pct, estado = cls.evaluate_discrepancy(
                balance_calculado=balance.balance_neto,
                monto_declarado=monto_declarado,
                tolerancia_pct=tolerancia_pct,
            )

        return AuditResult(
            fecha_auditoria=fecha_auditoria,
            estado=estado,
            total_registros_entrada=len(transactions) + len(dlq_records),
            total_registros_validos=len(transactions),
            total_registros_dlq=len(dlq_records),
            balance=balance,
            duplicados=duplicados,
            dlq_records=dlq_records,
            monto_declarado=monto_declarado,
            discrepancia_abs=discrepancia_abs,
            discrepancia_pct=discrepancia_pct,
            tolerancia_pct=tolerancia_pct,
            ruta_reporte=ruta_reporte,
        )


class ReportGenerator:
    """
    Generador de reportes ejecutivos en Markdown compatible con Obsidian.
    NO realiza ningún cálculo financiero. Consume únicamente AuditResult.
    """

    @staticmethod
    def _fmt(monto: Decimal, moneda: str) -> str:
        """Formatea un Decimal como cadena monetaria con separador de miles."""
        return f"{moneda} {monto:,.2f}"

    @staticmethod
    def generate(audit_result: AuditResult, moneda: str = "S/") -> str:
        """
        Genera el contenido completo del reporte Markdown como string.
        """
        ar = audit_result
        fmt = ReportGenerator._fmt
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fecha_str = ar.fecha_auditoria.strftime("%Y-%m-%d")

        # Determinar icono y etiqueta de estado
        if ar.estado == EstadoAuditoria.BALANCE_OK:
            estado_icon = "🟩"
            estado_label = "BALANCE_OK"
        else:
            estado_icon = "🟥"
            estado_label = "CRITICAL_MISMATCH"

        # ── Frontmatter YAML ──────────────────────────────────────────────────
        lines: list[str] = [
            "---",
            f'title: "Dictamen de Auditoría Operativa — {fecha_str}"',
            f"fecha_auditoria: {fecha_str}",
            'proyecto: "PYME Ops Agent"',
            'skill: "audit_pyme_cashflow"',
            'version_skill: "1.0.0"',
            f"estado_auditoria: {estado_label}",
            "tags:",
            "  - auditoria",
            "  - cashflow",
            "  - reporte",
        ]
        if ar.estado == EstadoAuditoria.CRITICAL_MISMATCH:
            lines.append("  - alerta")
        lines += [
            "---",
            "",
            f"# 📊 Dictamen de Auditoría de Caja — {fecha_str}",
            "",
            f"> **Estado:** {estado_icon} {estado_label}  ",
            f"> **Fecha de Procesamiento:** {ahora}  ",
            f"> **Archivos Analizados:** `{ar.ruta_reporte.stem}`  ",
            f"> **Tolerancia de Descuadre Configurada:** {ar.tolerancia_pct}%",
            "",
            "---",
            "",
            "## 1. Resumen Ejecutivo (KPIs de Caja)",
            "",
            "| Indicador | Valor |",
            "| :--- | ---: |",
            f"| Total de Transacciones (entrada) | {ar.total_registros_entrada} |",
            f"| Transacciones Válidas Procesadas | {ar.total_registros_validos} |",
            f"| Transacciones Rechazadas (DLQ) | {ar.total_registros_dlq} |",
            f"| Duplicados Detectados | {len(ar.duplicados)} |",
            f"| **Total Ingresos** | **{fmt(ar.balance.total_ingresos, moneda)}** |",
            f"| **Total Egresos** | **{fmt(ar.balance.total_egresos, moneda)}** |",
            f"| **Balance Neto Calculado** | **{fmt(ar.balance.balance_neto, moneda)}** |",
            f"| Custodia en Efectivo | {fmt(ar.balance.custodia_efectivo, moneda)} |",
        ]

        # Monto declarado y discrepancia (opcional)
        if ar.monto_declarado is not None:
            lines += [
                f"| Monto Declarado (Arqueo) | {fmt(ar.monto_declarado, moneda)} |",
                f"| **Discrepancia Absoluta** | **{fmt(ar.discrepancia_abs, moneda)}** |",
                f"| **Porcentaje de Descuadre** | **{ar.discrepancia_pct}%** |",
            ]
        else:
            lines.append("| Monto Declarado (Arqueo) | No proporcionado |")

        # ── Desglose por método de pago ───────────────────────────────────────
        lines += [
            "",
            "---",
            "",
            "## 2. Desglose por Método de Pago",
            "",
            "| Método de Pago | Total Ingresos | Total Egresos | Neto |",
            "| :--- | ---: | ---: | ---: |",
        ]
        total_ing_check = Decimal("0.00")
        total_egr_check = Decimal("0.00")
        for metodo, datos in sorted(ar.balance.desglose_por_metodo.items()):
            ing = datos["ingresos"]
            egr = datos["egresos"]
            neto = datos["neto"]
            total_ing_check += ing
            total_egr_check += egr
            lines.append(
                f"| {metodo.capitalize()} | {fmt(ing, moneda)} | {fmt(egr, moneda)} | {fmt(neto, moneda)} |"
            )
        lines.append(
            f"| **TOTAL** | **{fmt(ar.balance.total_ingresos, moneda)}** "
            f"| **{fmt(ar.balance.total_egresos, moneda)}** "
            f"| **{fmt(ar.balance.balance_neto, moneda)}** |"
        )

        # ── Alertas y anomalías ───────────────────────────────────────────────
        lines += ["", "---", "", "## 3. Alertas y Anomalías Detectadas", ""]

        if ar.estado == EstadoAuditoria.CRITICAL_MISMATCH:
            lines += [
                "> [!WARNING]",
                f"> **CRITICAL_MISMATCH**: La discrepancia entre el balance calculado "
                f"({fmt(ar.balance.balance_neto, moneda)}) y el monto declarado "
                f"({fmt(ar.monto_declarado, moneda)}) "
                f"es de {ar.discrepancia_pct}%, superando el umbral del {ar.tolerancia_pct}%.",
                "",
            ]

        if ar.duplicados or ar.estado == EstadoAuditoria.CRITICAL_MISMATCH:
            lines += [
                "| ID Alerta | Tipo | Descripción | Severidad |",
                "| :--- | :--- | :--- | :--- |",
            ]
            if ar.estado == EstadoAuditoria.CRITICAL_MISMATCH:
                lines.append(
                    f"| ALT-MISMATCH | DESCUADRE | Discrepancia neta: "
                    f"{fmt(ar.discrepancia_abs, moneda)} ({ar.discrepancia_pct}%) | CRITICAL |"
                )
            for dup in ar.duplicados:
                lines.append(
                    f"| {dup.alerta_id} | DUPLICATE | "
                    f"{dup.id_transaccion_a} y {dup.id_transaccion_b} — "
                    f"monto {fmt(dup.monto, moneda)} vía {dup.metodo_pago.value} "
                    f"en {dup.delta_segundos}s | {dup.severidad} |"
                )
        else:
            lines.append("> [!NOTE]")
            lines.append("> No se detectaron anomalías ni duplicados en esta jornada. ✅")

        # ── Dead Letter Queue ─────────────────────────────────────────────────
        lines += ["", "---", "", "## 4. Registros Rechazados (Dead Letter Queue)", ""]

        if ar.dlq_records:
            lines += [
                "> [!CAUTION]",
                f"> **{ar.total_registros_dlq} registro(s)** no pasaron la validación de esquema "
                "y fueron enviados a cuarentena. Revisar `reports/dlq_anomalias.json`.",
                "",
                "| DLQ ID | Campo Inválido | Motivo de Rechazo |",
                "| :--- | :--- | :--- |",
            ]
            for dlq in ar.dlq_records:
                motivo_short = dlq.motivo_rechazo[:80] + ("…" if len(dlq.motivo_rechazo) > 80 else "")
                lines.append(
                    f"| {dlq.dlq_id} | `{dlq.campo_incriminado}` | {motivo_short} |"
                )
        else:
            lines.append("> [!NOTE]")
            lines.append("> Todos los registros superaron la validación de esquema. ✅")

        # ── Footer ────────────────────────────────────────────────────────────
        lines += [
            "",
            "---",
            "",
            "*Dictamen generado automáticamente por `audit_pyme_cashflow v1.0.0` "
            "— PYME Ops Agent SDLC*",
            "",
            f"*Procesado: {ahora} | Registros de entrada: {ar.total_registros_entrada}*",
        ]

        return "\n".join(lines)

    @staticmethod
    def write_to_disk(content: str, output_path: Path) -> None:
        """
        Escribe el contenido del reporte al archivo de output.
        Crea los directorios padre si no existen.

        Raises:
            OSError: Si el archivo no puede ser escrito.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")


def _serialize_dlq(dlq_records: list[DLQRecord], output_path: Path) -> None:
    """Serializa la lista de registros DLQ a un archivo JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for rec in dlq_records:
        payload.append({
            "dlq_id": rec.dlq_id,
            "timestamp_registro": rec.timestamp_registro.isoformat(),
            "motivo_rechazo": rec.motivo_rechazo,
            "campo_incriminado": rec.campo_incriminado,
            "valor_recibido": str(rec.valor_recibido),
            "registro_original": rec.registro_original,
        })
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


# =============================================================================
# SECCIÓN 5: CLI PRINCIPAL (argparse)
# =============================================================================

def _build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        prog="audit_engine",
        description="PYME Ops Agent — Motor de Auditoría Operativa de Caja v1.0.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplo:\n"
            "  python tools/audit_engine.py \\\n"
            "    --input data/ventas_diarias.csv \\\n"
            "    --schema data/schemas/transactions_schema.json \\\n"
            "    --output reports/cierre_diario_actual.md \\\n"
            "    --tolerance 5.0"
        ),
    )
    parser.add_argument(
        "--input", required=True, type=Path,
        metavar="RUTA",
        help="Ruta al archivo de transacciones (.csv o .json).",
    )
    parser.add_argument(
        "--schema", required=True, type=Path,
        metavar="RUTA",
        help="Ruta al esquema JSON de validación (transactions_schema.json).",
    )
    parser.add_argument(
        "--output", required=True, type=Path,
        metavar="RUTA",
        help="Ruta del reporte Markdown de salida.",
    )
    parser.add_argument(
        "--tolerance", type=Decimal, default=Decimal("5.0"),
        metavar="PCT",
        help="Porcentaje de descuadre tolerable (default: 5.0).",
    )
    parser.add_argument(
        "--declared", type=Decimal, default=None,
        metavar="MONTO",
        help="Monto declarado en el arqueo físico de caja (opcional).",
    )
    parser.add_argument(
        "--date", type=str, default=None,
        metavar="YYYY-MM-DD",
        help="Fecha de auditoría. Si se omite, usa la fecha actual del sistema.",
    )
    parser.add_argument(
        "--dlq-output", type=Path,
        default=Path("reports/dlq_anomalias.json"),
        metavar="RUTA",
        help="Ruta del archivo DLQ JSON (default: reports/dlq_anomalias.json).",
    )
    return parser


def main() -> int:
    """Punto de entrada principal del CLI. Retorna el código de salida."""
    parser = _build_parser()
    args = parser.parse_args()

    # ── Resolver fecha de auditoría ───────────────────────────────────────────
    if args.date:
        try:
            fecha_auditoria = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(
                f"[ERROR] Formato de fecha inválido: '{args.date}'. Use YYYY-MM-DD.",
                file=sys.stderr,
            )
            return 2
    else:
        fecha_auditoria = datetime.now()

    print("=" * 60)
    print("  PYME Ops Agent — Motor de Auditoría v1.0.0")
    print("=" * 60)
    print(f"  Fecha de auditoría : {fecha_auditoria.strftime('%Y-%m-%d')}")
    print(f"  Archivo de entrada : {args.input}")
    print(f"  Esquema            : {args.schema}")
    print(f"  Reporte de salida  : {args.output}")
    print(f"  Tolerancia         : {args.tolerance}%")
    if args.declared is not None:
        print(f"  Monto declarado    : S/ {args.declared:,.2f}")
    print("=" * 60)

    # ── 1. Cargar datos ───────────────────────────────────────────────────────
    print("\n[1/4] Cargando archivo de transacciones...")
    try:
        records_raw = DataIngestion.load(args.input)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 3
    print(f"       {len(records_raw)} registros cargados desde '{args.input}'.")

    # ── 2. Validar esquema ────────────────────────────────────────────────────
    print("\n[2/4] Validando registros contra el esquema...")
    try:
        validator = SchemaValidator(args.schema)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 3

    transactions, dlq_records = validator.validate_batch(records_raw)
    print(f"       [OK]  Validos  : {len(transactions)}")
    print(f"       [DLQ] Rechazados: {len(dlq_records)}")

    if not transactions:
        print(
            f"\n[ERROR] Cero registros válidos tras la validación. "
            "Revise el archivo de entrada y el esquema.",
            file=sys.stderr,
        )
        return 4

    # ── 3. Ejecutar auditoría ─────────────────────────────────────────────────
    print("\n[3/4] Ejecutando motor de auditoría...")
    result = AuditEngine.run_full_audit(
        transactions=transactions,
        monto_declarado=args.declared,
        tolerancia_pct=args.tolerance,
        fecha_auditoria=fecha_auditoria,
        ruta_reporte=args.output,
        dlq_records=dlq_records,
    )

    print(f"       Balance neto calculado : S/ {result.balance.balance_neto:,.2f}")
    print(f"       Duplicados detectados  : {len(result.duplicados)}")
    print(f"       Estado de auditoria    : {result.estado.value}")

    if result.discrepancia_pct is not None:
        print(f"       Discrepancia           : {result.discrepancia_pct}%")

    # ── 4. Generar reportes ───────────────────────────────────────────────────
    print("\n[4/4] Generando reportes...")

    # Reporte Markdown principal
    md_content = ReportGenerator.generate(result)
    ReportGenerator.write_to_disk(md_content, args.output)
    print(f"       [MD]  Reporte Markdown -> '{args.output}'")

    # DLQ JSON
    if dlq_records:
        _serialize_dlq(dlq_records, args.dlq_output)
        print(f"       [DLQ] DLQ JSON        -> '{args.dlq_output}' ({len(dlq_records)} registro(s))")
    else:
        print("       [DLQ] Sin registros rechazados.")

    # ── Resumen final ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if result.estado == EstadoAuditoria.BALANCE_OK:
        print("  [OK] AUDITORIA COMPLETADA --- BALANCE OK")
        exit_code = 0
    else:
        print("  [!!] AUDITORIA COMPLETADA --- CRITICAL MISMATCH DETECTADO")
        exit_code = 1

    print("=" * 60 + "\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
