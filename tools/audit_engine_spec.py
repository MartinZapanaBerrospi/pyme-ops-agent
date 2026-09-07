"""
=============================================================================
PYME Ops Agent — Especificación Formal de Interfaz del Motor de Auditoría
=============================================================================
Documento  : tools/audit_engine_spec.py
Fase SDLC  : 03 - Diseño del Sistema
Autor      : System Architect Agent
Estado     : SPEC APROBADA — Pendiente de implementación por Software Engineer
Versión    : 1.0.0

INSTRUCCIÓN PARA SOFTWARE ENGINEER:
    Este archivo es el CONTRATO DE INTERFAZ formal de la Fase 3.
    El Software Engineer (Fase 4) debe implementar todos los métodos aquí
    especificados respetando:
      - Los Type Hints exactos de cada firma.
      - Las excepciones personalizadas definidas.
      - Las garantías de idempotencia y pureza funcional.
      - El uso EXCLUSIVO de decimal.Decimal para todos los montos monetarios.

    NO MODIFICAR LAS FIRMAS. Solo añadir el cuerpo de implementación.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
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
# SECCIÓN 2: EXCEPCIONES PERSONALIZADAS DEL DOMINIO
# =============================================================================

class PymeOpsAgentBaseError(Exception):
    """Excepción raíz del sistema. Todas las excepciones del dominio la heredan."""
    pass


class DataValidationError(PymeOpsAgentBaseError):
    """
    Se lanza cuando un registro de transacción no cumple el contrato formal
    definido en transactions_schema.json.

    Atributos:
        registro_id (str): ID del registro que falló la validación.
        campo (str): Nombre del campo que contiene el valor inválido.
        valor_recibido: El valor inválido tal como fue recibido.
        motivo (str): Descripción detallada del motivo de rechazo.

    Ejemplo de uso:
        raise DataValidationError(
            registro_id="TRX-099",
            campo="monto",
            valor_recibido="veinte",
            motivo="El campo 'monto' debe ser un número mayor a 0."
        )
    """
    def __init__(
        self,
        registro_id: str,
        campo: str,
        valor_recibido: object,
        motivo: str,
    ) -> None:
        self.registro_id = registro_id
        self.campo = campo
        self.valor_recibido = valor_recibido
        self.motivo = motivo
        super().__init__(
            f"[DataValidationError] ID={registro_id} | campo='{campo}' | "
            f"valor={repr(valor_recibido)} | motivo={motivo}"
        )


class DiscrepancyThresholdExceeded(PymeOpsAgentBaseError):
    """
    Se lanza cuando la discrepancia entre el balance calculado por el motor
    y el monto declarado en el arqueo físico supera el umbral de tolerancia.

    Atributos:
        balance_calculado (Decimal): Monto neto calculado por el motor.
        monto_declarado (Decimal): Monto declarado manualmente en el arqueo físico.
        discrepancia_abs (Decimal): Diferencia absoluta en unidades monetarias.
        discrepancia_pct (Decimal): Porcentaje de discrepancia sobre el calculado.
        tolerancia_pct (Decimal): Umbral de tolerancia configurado por el operador.

    Ejemplo de uso:
        raise DiscrepancyThresholdExceeded(
            balance_calculado=Decimal("5000.00"),
            monto_declarado=Decimal("4700.00"),
            discrepancia_abs=Decimal("300.00"),
            discrepancia_pct=Decimal("6.00"),
            tolerancia_pct=Decimal("5.00"),
        )
    """
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
    """
    Se lanza cuando el archivo de entrada no contiene ningún registro
    procesable tras la etapa de validación de esquemas.

    Ejemplo de uso:
        raise EmptyDatasetError(ruta_archivo=Path("data/input/transactions_2026-09-07.csv"))
    """
    def __init__(self, ruta_archivo: Path) -> None:
        self.ruta_archivo = ruta_archivo
        super().__init__(
            f"[EmptyDatasetError] El archivo '{ruta_archivo}' no contiene "
            "registros válidos procesables tras la validación de esquema."
        )


# =============================================================================
# SECCIÓN 3: MODELOS DE DATOS (DATACLASSES)
# =============================================================================

@dataclass(frozen=True)
class Transaction:
    """
    Representación inmutable y tipada de una transacción operativa validada.
    Solo se instancia DESPUÉS de pasar exitosamente la validación de esquema.
    El campo `monto` es SIEMPRE Decimal. Nunca float.
    """
    id_transaccion: str
    timestamp: datetime
    tipo: TipoTransaccion
    metodo_pago: MetodoPago
    monto: Decimal
    categoria: str
    estado: EstadoTransaccion
    referencia: Optional[str] = None
    descripcion: Optional[str] = None


@dataclass
class DLQRecord:
    """
    Envelope de cuarentena para un registro que no superó la validación de esquema.
    Se serializa a JSON Lines en data/dlq/YYYY-MM-DD_anomalies.jsonl.
    """
    dlq_id: str
    timestamp_registro: datetime
    motivo_rechazo: str
    campo_incriminado: str
    valor_recibido: object
    registro_original: dict


@dataclass
class DuplicateAlert:
    """
    Alerta generada cuando se detectan dos transacciones potencialmente duplicadas
    dentro de la ventana temporal crítica (≤ 180 segundos por defecto).
    """
    alerta_id: str
    id_transaccion_a: str
    id_transaccion_b: str
    monto: Decimal
    metodo_pago: MetodoPago
    delta_segundos: float
    severidad: str = "MEDIUM"


@dataclass
class BalanceSummary:
    """
    Resumen consolidado de balances financieros calculados por el motor.
    Todos los campos monetarios son Decimal para garantizar precisión exacta.
    """
    total_ingresos: Decimal = Decimal("0.00")
    total_egresos: Decimal = Decimal("0.00")
    balance_neto: Decimal = Decimal("0.00")
    custodia_efectivo: Decimal = Decimal("0.00")
    desglose_por_metodo: dict[str, dict[str, Decimal]] = field(default_factory=dict)


@dataclass
class AuditResult:
    """
    Estructura de datos de salida del motor de auditoría.
    Encapsula todos los resultados de la ejecución para ser consumidos
    por el generador de reportes (report_gen.py).
    """
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
# SECCIÓN 4: CONTRATOS DE INTERFAZ DE MÓDULOS
# =============================================================================

class SchemaValidator:
    """
    Módulo de validación de registros contra el contrato JSON Schema formal.

    IMPLEMENTACIÓN REQUERIDA (Fase 4 — Software Engineer):
        El constructor debe cargar el esquema JSON desde la ruta provista y
        almacenarlo en memoria para validación eficiente de todos los registros.
    """

    def __init__(self, schema_path: Path) -> None:
        """
        Carga el esquema JSON Schema desde disco.

        Args:
            schema_path: Ruta al archivo transactions_schema.json.

        Raises:
            FileNotFoundError: Si el archivo de esquema no existe.
            ValueError: Si el contenido del archivo no es un JSON válido.
        """
        raise NotImplementedError("Fase 4: Implementar carga del esquema JSON.")

    def validate_record(self, record: dict) -> Transaction:
        """
        Valida un único registro raw contra el esquema y lo convierte
        al dataclass Transaction tipado.

        Args:
            record: Diccionario raw del registro tal como fue leído del CSV/JSON.

        Returns:
            Transaction: Instancia inmutable y completamente tipada del registro.

        Raises:
            DataValidationError: Si el registro viola alguna regla del esquema.
        """
        raise NotImplementedError("Fase 4: Implementar validación de registro.")

    def validate_batch(
        self, records: list[dict]
    ) -> tuple[list[Transaction], list[DLQRecord]]:
        """
        Valida una lista completa de registros raw, separando válidos de inválidos.

        Args:
            records: Lista de registros raw leídos del archivo de entrada.

        Returns:
            tuple: (lista de Transaction válidas, lista de DLQRecord rechazados)
        """
        raise NotImplementedError("Fase 4: Implementar validación en batch.")


class AuditEngine:
    """
    Motor de auditoría determinista y puro.
    GARANTÍA: Todas las funciones son puras — mismo input → mismo output.
    PROHIBIDO: Efectos secundarios, escritura a disco, llamadas a red.
    """

    VENTANA_DUPLICADO_SEG: int = 180  # Ventana temporal crítica para detección de duplicados.

    @staticmethod
    def detect_duplicates(
        transactions: list[Transaction],
        ventana_segundos: int = VENTANA_DUPLICADO_SEG,
    ) -> list[DuplicateAlert]:
        """
        Detecta transacciones potencialmente duplicadas dentro de una ventana
        temporal crítica, comparando monto, método de pago y referencia.

        COMPLEJIDAD ESPERADA: O(n²) en el peor caso. Aceptable para n ≤ 10,000.

        Args:
            transactions: Lista de transacciones validadas ordenadas por timestamp.
            ventana_segundos: Máximo delta de tiempo en segundos para considerar
                              dos transacciones como candidatas a duplicado.

        Returns:
            list[DuplicateAlert]: Lista de alertas de posibles duplicados detectados.
        """
        raise NotImplementedError("Fase 4: Implementar detección de duplicados.")

    @staticmethod
    def calculate_balance(transactions: list[Transaction]) -> BalanceSummary:
        """
        Calcula el balance financiero completo de la jornada auditada.
        Usa exclusivamente decimal.Decimal. Prohibido el uso de float.

        Fórmulas aplicadas:
            total_ingresos = sum(t.monto for t in transactions if t.tipo == INGRESO and t.estado == COMPLETADO)
            total_egresos  = sum(t.monto for t in transactions if t.tipo == EGRESO  and t.estado == COMPLETADO)
            balance_neto   = total_ingresos - total_egresos
            custodia_efectivo = sum(t.monto for t in transactions
                                    if t.metodo_pago == EFECTIVO and t.tipo == INGRESO
                                    and t.estado == COMPLETADO)
                                - sum(t.monto for t in transactions
                                    if t.metodo_pago == EFECTIVO and t.tipo == EGRESO
                                    and t.estado == COMPLETADO)

        Args:
            transactions: Lista de transacciones validadas a consolidar.

        Returns:
            BalanceSummary: Resumen completo con todos los totales y desgloses.
        """
        raise NotImplementedError("Fase 4: Implementar cálculo de balance.")

    @staticmethod
    def evaluate_discrepancy(
        balance_calculado: Decimal,
        monto_declarado: Decimal,
        tolerancia_pct: Decimal,
    ) -> tuple[Decimal, Decimal, EstadoAuditoria]:
        """
        Evalúa la discrepancia entre el balance calculado y el arqueo declarado.

        Fórmulas:
            discrepancia_abs = abs(balance_calculado - monto_declarado)
            discrepancia_pct = (discrepancia_abs / balance_calculado) * 100
            estado = CRITICAL_MISMATCH si discrepancia_pct > tolerancia_pct, BALANCE_OK en caso contrario.

        Args:
            balance_calculado: Balance neto exacto calculado por el motor.
            monto_declarado: Monto declarado en el arqueo físico por el cajero.
            tolerancia_pct: Umbral porcentual de descuadre tolerable (por defecto 5.0).

        Returns:
            tuple: (discrepancia_abs, discrepancia_pct, EstadoAuditoria)

        Raises:
            DiscrepancyThresholdExceeded: Si la discrepancia supera el umbral.
                (NOTA: El caller decide si captura esta excepción o la deja propagar)
        """
        raise NotImplementedError("Fase 4: Implementar evaluación de discrepancia.")

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
        Orquesta la auditoría completa: detección de duplicados, cálculo de balance
        y evaluación de discrepancias, produciendo el AuditResult final.

        Args:
            transactions: Lista de transacciones válidas a auditar.
            monto_declarado: Monto del arqueo físico (None si no se proporcionó).
            tolerancia_pct: Umbral de descuadre como porcentaje (ej. Decimal("5.0")).
            fecha_auditoria: Fecha del cierre de jornada auditado.
            ruta_reporte: Ruta destino donde se escribirá el reporte Markdown.
            dlq_records: Registros enviados a DLQ durante la validación.

        Returns:
            AuditResult: Resultado completo de la auditoría listo para serialización.
        """
        raise NotImplementedError("Fase 4: Implementar orquestación completa de auditoría.")


class ReportGenerator:
    """
    Generador de reportes ejecutivos en Markdown compatible con Obsidian.
    Consume únicamente el AuditResult producido por AuditEngine.
    NO realiza ningún cálculo financiero propio.
    """

    @staticmethod
    def generate(
        audit_result: AuditResult,
        moneda: str = "S/",
    ) -> str:
        """
        Genera el contenido completo del reporte Markdown como string.
        El caller es responsable de escribir el string al archivo de output.

        Args:
            audit_result: Resultado completo de la auditoría.
            moneda: Prefijo de la moneda a usar en los montos (default: "S/").

        Returns:
            str: Contenido del reporte ejecutivo en formato Markdown estructurado,
                 con frontmatter YAML, tablas GFM y callouts de Obsidian.
        """
        raise NotImplementedError("Fase 4: Implementar generador de reporte Markdown.")

    @staticmethod
    def write_to_disk(content: str, output_path: Path) -> None:
        """
        Escribe el contenido del reporte generado al archivo de output.

        Args:
            content: Contenido del reporte Markdown como string.
            output_path: Ruta destino del archivo. Se crean los directorios
                         padre si no existen.

        Raises:
            OSError: Si el archivo no puede ser escrito por permisos o espacio en disco.
        """
        raise NotImplementedError("Fase 4: Implementar escritura del reporte a disco.")


class DataIngestion:
    """
    Módulo de carga y parseo de archivos de transacciones desde disco.
    Soporte para CSV y JSON. Inmutable respecto al archivo de origen.
    """

    @staticmethod
    def load_csv(file_path: Path) -> list[dict]:
        """
        Lee un archivo CSV de transacciones y devuelve una lista de diccionarios raw.

        Args:
            file_path: Ruta al archivo CSV de transacciones.

        Returns:
            list[dict]: Lista de registros sin validar, listos para SchemaValidator.

        Raises:
            FileNotFoundError: Si el archivo no existe en la ruta especificada.
            ValueError: Si el archivo CSV no tiene el encabezado esperado.
        """
        raise NotImplementedError("Fase 4: Implementar carga de CSV.")

    @staticmethod
    def load_json(file_path: Path) -> list[dict]:
        """
        Lee un archivo JSON de transacciones y devuelve una lista de diccionarios raw.

        Args:
            file_path: Ruta al archivo JSON (debe ser un array de objetos).

        Returns:
            list[dict]: Lista de registros sin validar.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            ValueError: Si el JSON no es un array en la raíz.
        """
        raise NotImplementedError("Fase 4: Implementar carga de JSON.")

    @classmethod
    def load(cls, file_path: Path) -> list[dict]:
        """
        Punto de entrada unificado. Detecta el formato por extensión del archivo.

        Args:
            file_path: Ruta al archivo (.csv o .json).

        Returns:
            list[dict]: Registros raw listos para validación.

        Raises:
            ValueError: Si la extensión del archivo no es .csv ni .json.
        """
        raise NotImplementedError("Fase 4: Implementar dispatcher de carga unificado.")
