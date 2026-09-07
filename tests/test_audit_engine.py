"""
=============================================================================
PYME Ops Agent — Suite de Pruebas Automatizadas (Fase 5: Testing)
=============================================================================
Archivo   : tests/test_audit_engine.py
Fase SDLC : 05 - Pruebas y Verificación
Rol       : QA Engineer Agent (sops/roles/04_qa_engineer.md)
Tecnología: Python unittest (Librería estándar, cero dependencias de terceros)
=============================================================================
"""

import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
import unittest

from tools.audit_engine import (
    AuditEngine,
    AuditResult,
    BalanceSummary,
    DataIngestion,
    DataValidationError,
    DiscrepancyThresholdExceeded,
    DLQRecord,
    DuplicateAlert,
    EmptyDatasetError,
    EstadoAuditoria,
    EstadoTransaccion,
    MetodoPago,
    PymeOpsAgentBaseError,
    ReportGenerator,
    SchemaValidator,
    TipoTransaccion,
    Transaction,
)


class TestPrecisionMonetaria(unittest.TestCase):
    """
    Verifica que todos los cálculos contables operen bajo aritmética exacta
    con Decimal, eliminando por completo cualquier error de coma flotante (float rounding).
    """

    def setUp(self) -> None:
        self.base_time = datetime(2026, 9, 7, 10, 0, 0)

    def test_precision_decimal_sin_deriva_flotante(self) -> None:
        """
        Prueba clásica de precisión: 0.10 + 0.20 debe ser exactamente 0.30,
        no 0.30000000000000004 como ocurre en float binario.
        """
        t1 = Transaction(
            id_transaccion="TX-001",
            timestamp=self.base_time,
            tipo=TipoTransaccion.INGRESO,
            metodo_pago=MetodoPago.EFECTIVO,
            monto=Decimal("0.10"),
            categoria="Centavos",
            estado=EstadoTransaccion.COMPLETADO,
        )
        t2 = Transaction(
            id_transaccion="TX-002",
            timestamp=self.base_time + timedelta(minutes=1),
            tipo=TipoTransaccion.INGRESO,
            metodo_pago=MetodoPago.EFECTIVO,
            monto=Decimal("0.20"),
            categoria="Centavos",
            estado=EstadoTransaccion.COMPLETADO,
        )

        balance = AuditEngine.calculate_balance([t1, t2])
        self.assertEqual(balance.total_ingresos, Decimal("0.30"))
        self.assertEqual(balance.balance_neto, Decimal("0.30"))
        self.assertIsInstance(balance.balance_neto, Decimal)
        self.assertNotIsInstance(balance.balance_neto, float)

    def test_acumulacion_de_fracciones_centecimales(self) -> None:
        """
        Suma 100 transacciones de S/ 0.33 y 100 transacciones de S/ 0.67.
        Total exacto = 100 * 0.33 (33.00) + 100 * 0.67 (67.00) = 100.00 exacto.
        """
        transactions = []
        for i in range(100):
            transactions.append(
                Transaction(
                    id_transaccion=f"TX-A-{i:03d}",
                    timestamp=self.base_time + timedelta(seconds=i * 5),
                    tipo=TipoTransaccion.INGRESO,
                    metodo_pago=MetodoPago.POS,
                    monto=Decimal("0.33"),
                    categoria="Micropago",
                    estado=EstadoTransaccion.COMPLETADO,
                )
            )
            transactions.append(
                Transaction(
                    id_transaccion=f"TX-B-{i:03d}",
                    timestamp=self.base_time + timedelta(seconds=i * 5 + 1),
                    tipo=TipoTransaccion.INGRESO,
                    metodo_pago=MetodoPago.YAPE,
                    monto=Decimal("0.67"),
                    categoria="Micropago",
                    estado=EstadoTransaccion.COMPLETADO,
                )
            )

        balance = AuditEngine.calculate_balance(transactions)
        self.assertEqual(balance.total_ingresos, Decimal("100.00"))
        self.assertEqual(balance.total_egresos, Decimal("0.00"))
        self.assertEqual(balance.balance_neto, Decimal("100.00"))

    def test_custodia_efectivo_solo_considera_efectivo(self) -> None:
        """
        Verifica que el dinero en custodia física distinga entre efectivo y canales digitales.
        Ingreso efectivo: S/ 500, Egreso efectivo: S/ 150 -> Custodia = S/ 350.
        Ingreso POS: S/ 1000 -> No entra en custodia física.
        """
        txs = [
            Transaction("TX-EF-1", self.base_time, TipoTransaccion.INGRESO, MetodoPago.EFECTIVO, Decimal("500.00"), "Venta", EstadoTransaccion.COMPLETADO),
            Transaction("TX-EF-2", self.base_time, TipoTransaccion.EGRESO, MetodoPago.EFECTIVO, Decimal("150.00"), "Gasto", EstadoTransaccion.COMPLETADO),
            Transaction("TX-POS-1", self.base_time, TipoTransaccion.INGRESO, MetodoPago.POS, Decimal("1000.00"), "Venta", EstadoTransaccion.COMPLETADO),
        ]
        balance = AuditEngine.calculate_balance(txs)
        self.assertEqual(balance.total_ingresos, Decimal("1500.00"))
        self.assertEqual(balance.total_egresos, Decimal("150.00"))
        self.assertEqual(balance.balance_neto, Decimal("1350.00"))
        self.assertEqual(balance.custodia_efectivo, Decimal("350.00"))


class TestDLQToleranciaFallos(unittest.TestCase):
    """
    Verifica que el motor sea resiliente y aísle registros malformados o corruptos
    hacia el Dead Letter Queue (DLQ) sin interrumpir la ejecución.
    """

    def setUp(self) -> None:
        self.schema_path = Path("data/schemas/transactions_schema.json")
        self.validator = SchemaValidator(self.schema_path)

    def test_aislamiento_de_registros_corruptos(self) -> None:
        """
        Inyecta deliberadamente registros inválidos y confirma su aislamiento al DLQ.
        """
        registros_corruptos = [
            # 1. Monto negativo
            {
                "id_transaccion": "BAD-001",
                "timestamp": "2026-09-07T10:00:00Z",
                "tipo": "ingreso",
                "metodo_pago": "efectivo",
                "monto": -100.00,
                "categoria": "Venta",
                "estado": "completado"
            },
            # 2. Monto cero
            {
                "id_transaccion": "BAD-002",
                "timestamp": "2026-09-07T10:00:00Z",
                "tipo": "ingreso",
                "metodo_pago": "efectivo",
                "monto": 0.00,
                "categoria": "Venta",
                "estado": "completado"
            },
            # 3. Monto no numérico
            {
                "id_transaccion": "BAD-003",
                "timestamp": "2026-09-07T10:00:00Z",
                "tipo": "ingreso",
                "metodo_pago": "efectivo",
                "monto": "quinientos_soles",
                "categoria": "Venta",
                "estado": "completado"
            },
            # 4. Timestamp malformado
            {
                "id_transaccion": "BAD-004",
                "timestamp": "FECHA_INVALIDA_2026",
                "tipo": "ingreso",
                "metodo_pago": "efectivo",
                "monto": 50.00,
                "categoria": "Venta",
                "estado": "completado"
            },
            # 5. Tipo contable inexistente
            {
                "id_transaccion": "BAD-005",
                "timestamp": "2026-09-07T10:00:00Z",
                "tipo": "prestamo_no_autorizado",
                "metodo_pago": "efectivo",
                "monto": 50.00,
                "categoria": "Venta",
                "estado": "completado"
            },
            # 6. Medio de pago fuera de catálogo
            {
                "id_transaccion": "BAD-006",
                "timestamp": "2026-09-07T10:00:00Z",
                "tipo": "ingreso",
                "metodo_pago": "criptomoneda",
                "monto": 50.00,
                "categoria": "Venta",
                "estado": "completado"
            },
            # 7. Campo obligatorio faltante (sin categoría)
            {
                "id_transaccion": "BAD-007",
                "timestamp": "2026-09-07T10:00:00Z",
                "tipo": "ingreso",
                "metodo_pago": "efectivo",
                "monto": 50.00,
                "estado": "completado"
            },
        ]

        validos, dlq = self.validator.validate_batch(registros_corruptos)

        self.assertEqual(len(validos), 0)
        self.assertEqual(len(dlq), 7)
        for item in dlq:
            self.assertIsInstance(item, DLQRecord)
            self.assertTrue(item.dlq_id.startswith("DLQ-"))
            self.assertTrue(len(item.motivo_rechazo) > 0)

    def test_lote_mixto_separa_validos_e_invalidos_sin_romper(self) -> None:
        """
        Verifica que en un lote mixto los válidos continúen hacia el motor
        mientras los defectuosos son desviados al DLQ.
        """
        lote_mixto = [
            {
                "id_transaccion": "OK-001",
                "timestamp": "2026-09-07T10:00:00Z",
                "tipo": "ingreso",
                "metodo_pago": "efectivo",
                "monto": 120.50,
                "categoria": "Venta",
                "estado": "completado",
            },
            {
                "id_transaccion": "BAD-001",
                "timestamp": "2026-09-07T10:00:00Z",
                "tipo": "invalido",
                "metodo_pago": "efectivo",
                "monto": 100.00,
                "categoria": "Venta",
                "estado": "completado",
            },
            {
                "id_transaccion": "OK-002",
                "timestamp": "2026-09-07T10:05:00Z",
                "tipo": "egreso",
                "metodo_pago": "yape",
                "monto": 25.00,
                "categoria": "Insumos",
                "estado": "completado",
            },
        ]

        validos, dlq = self.validator.validate_batch(lote_mixto)
        self.assertEqual(len(validos), 2)
        self.assertEqual(len(dlq), 1)
        self.assertEqual(validos[0].id_transaccion, "OK-001")
        self.assertEqual(validos[1].id_transaccion, "OK-002")
        self.assertEqual(dlq[0].campo_incriminado, "tipo")


class TestDeteccionDuplicados(unittest.TestCase):
    """
    Verifica la detección algorítmica de transacciones redundantes
    dentro de la ventana temporal crítica (<= 180 segundos).
    """

    def setUp(self) -> None:
        self.t0 = datetime(2026, 9, 7, 12, 0, 0)

    def test_duplicados_en_30s_60s_120s(self) -> None:
        """
        Transacciones idénticas (monto, método, referencia) con deltas de 30s, 60s y 120s
        deben ser detectadas como duplicadas al estar dentro de la ventana de 180 segundos.
        """
        # Par 1: Delta = 30 segundos
        tx1 = Transaction("TX-A1", self.t0, TipoTransaccion.INGRESO, MetodoPago.YAPE, Decimal("50.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-001")
        tx2 = Transaction("TX-A2", self.t0 + timedelta(seconds=30), TipoTransaccion.INGRESO, MetodoPago.YAPE, Decimal("50.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-001")

        dups_30 = AuditEngine.detect_duplicates([tx1, tx2])
        self.assertEqual(len(dups_30), 1)
        self.assertEqual(dups_30[0].delta_segundos, 30.0)

        # Par 2: Delta = 60 segundos
        tx3 = Transaction("TX-B1", self.t0, TipoTransaccion.INGRESO, MetodoPago.PLIN, Decimal("80.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-002")
        tx4 = Transaction("TX-B2", self.t0 + timedelta(seconds=60), TipoTransaccion.INGRESO, MetodoPago.PLIN, Decimal("80.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-002")

        dups_60 = AuditEngine.detect_duplicates([tx3, tx4])
        self.assertEqual(len(dups_60), 1)
        self.assertEqual(dups_60[0].delta_segundos, 60.0)

        # Par 3: Delta = 120 segundos
        tx5 = Transaction("TX-C1", self.t0, TipoTransaccion.INGRESO, MetodoPago.POS, Decimal("150.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-003")
        tx6 = Transaction("TX-C2", self.t0 + timedelta(seconds=120), TipoTransaccion.INGRESO, MetodoPago.POS, Decimal("150.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-003")

        dups_120 = AuditEngine.detect_duplicates([tx5, tx6])
        self.assertEqual(len(dups_120), 1)
        self.assertEqual(dups_120[0].delta_segundos, 120.0)

    def test_transacciones_fuera_de_ventana_no_son_duplicadas(self) -> None:
        """
        Transacciones idénticas separadas por más de 180 segundos (ej. 200s)
        no deben marcarse como duplicadas.
        """
        tx1 = Transaction("TX-D1", self.t0, TipoTransaccion.INGRESO, MetodoPago.EFECTIVO, Decimal("100.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-004")
        tx2 = Transaction("TX-D2", self.t0 + timedelta(seconds=200), TipoTransaccion.INGRESO, MetodoPago.EFECTIVO, Decimal("100.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-004")

        dups = AuditEngine.detect_duplicates([tx1, tx2])
        self.assertEqual(len(dups), 0)

    def test_transacciones_en_ventana_con_diferencias_no_son_duplicadas(self) -> None:
        """
        Transacciones dentro de 30 segundos pero con diferente referencia, monto o método
        son legítimas y no deben disparar falso positivo.
        """
        # Diferente monto
        tx1 = Transaction("TX-E1", self.t0, TipoTransaccion.INGRESO, MetodoPago.EFECTIVO, Decimal("100.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-100")
        tx2 = Transaction("TX-E2", self.t0 + timedelta(seconds=15), TipoTransaccion.INGRESO, MetodoPago.EFECTIVO, Decimal("105.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-100")

        # Diferente referencia
        tx3 = Transaction("TX-E3", self.t0, TipoTransaccion.INGRESO, MetodoPago.EFECTIVO, Decimal("100.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-200")
        tx4 = Transaction("TX-E4", self.t0 + timedelta(seconds=15), TipoTransaccion.INGRESO, MetodoPago.EFECTIVO, Decimal("100.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-201")

        # Diferente método
        tx5 = Transaction("TX-E5", self.t0, TipoTransaccion.INGRESO, MetodoPago.YAPE, Decimal("100.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-300")
        tx6 = Transaction("TX-E6", self.t0 + timedelta(seconds=15), TipoTransaccion.INGRESO, MetodoPago.PLIN, Decimal("100.00"), "Venta", EstadoTransaccion.COMPLETADO, referencia="REF-300")

        self.assertEqual(len(AuditEngine.detect_duplicates([tx1, tx2])), 0)
        self.assertEqual(len(AuditEngine.detect_duplicates([tx3, tx4])), 0)
        self.assertEqual(len(AuditEngine.detect_duplicates([tx5, tx6])), 0)


class TestUmbralDiscrepancia(unittest.TestCase):
    """
    Verifica que las discrepancias superiores al umbral de tolerancia (5%)
    generen el estado de alerta crítica (CRITICAL_MISMATCH) y que discrepancias
    dentro del margen tolerado permanezcan en BALANCE_OK.
    """

    def test_discrepancia_mayor_al_5_porciento_dispara_alerta(self) -> None:
        """
        Balance Calculado = S/ 1,000.00.
        Monto Declarado = S/ 920.00.
        Diferencia = S/ 80.00 (8.00% > 5.0% tolerancia).
        Resultado esperado: CRITICAL_MISMATCH.
        """
        calc = Decimal("1000.00")
        decl = Decimal("920.00")
        tol = Decimal("5.0")

        diff_abs, diff_pct, estado = AuditEngine.evaluate_discrepancy(calc, decl, tol)

        self.assertEqual(diff_abs, Decimal("80.00"))
        self.assertEqual(diff_pct, Decimal("8.00"))
        self.assertEqual(estado, EstadoAuditoria.CRITICAL_MISMATCH)

        # Verificar que si se solicita raise_on_exceeded, lance la excepción personalizada
        with self.assertRaises(DiscrepancyThresholdExceeded) as ctx:
            AuditEngine.evaluate_discrepancy(calc, decl, tol, raise_on_exceeded=True)
        self.assertEqual(ctx.exception.discrepancia_pct, Decimal("8.00"))

    def test_discrepancia_menor_o_igual_al_5_porciento_mantiene_balance_ok(self) -> None:
        """
        Balance Calculado = S/ 1,000.00.
        Monto Declarado = S/ 980.00.
        Diferencia = S/ 20.00 (2.00% <= 5.0% tolerancia).
        Resultado esperado: BALANCE_OK.
        """
        calc = Decimal("1000.00")
        decl = Decimal("980.00")
        tol = Decimal("5.0")

        diff_abs, diff_pct, estado = AuditEngine.evaluate_discrepancy(calc, decl, tol)

        self.assertEqual(diff_abs, Decimal("20.00"))
        self.assertEqual(diff_pct, Decimal("2.00"))
        self.assertEqual(estado, EstadoAuditoria.BALANCE_OK)

    def test_discrepancia_limite_exacto_5_porciento(self) -> None:
        """
        Exactamente 5.0% de diferencia debe ser aceptado dentro de la tolerancia (BALANCE_OK).
        """
        calc = Decimal("1000.00")
        decl = Decimal("950.00")
        tol = Decimal("5.0")

        diff_abs, diff_pct, estado = AuditEngine.evaluate_discrepancy(calc, decl, tol)
        self.assertEqual(diff_pct, Decimal("5.00"))
        self.assertEqual(estado, EstadoAuditoria.BALANCE_OK)


class TestDatasetVacio(unittest.TestCase):
    """
    Verifica que la ausencia de registros procesables genere
    la excepción controlada EmptyDatasetError sin provocar fallas no gestionadas.
    """

    def test_empty_dataset_error_lanzado_en_run_full_audit(self) -> None:
        """
        Invocación de run_full_audit con lista vacía de transacciones
        debe lanzar EmptyDatasetError.
        """
        with self.assertRaises(EmptyDatasetError) as ctx:
            AuditEngine.run_full_audit(
                transactions=[],
                monto_declarado=None,
                tolerancia_pct=Decimal("5.0"),
                fecha_auditoria=datetime(2026, 9, 7),
                ruta_reporte=Path("reports/dummy.md"),
                dlq_records=[],
            )

        self.assertEqual(ctx.exception.ruta_archivo, Path("reports/dummy.md"))
        self.assertIsInstance(ctx.exception, PymeOpsAgentBaseError)


class TestIntegracionFlujoCompleto(unittest.TestCase):
    """
    Prueba de integración extremo a extremo utilizando los archivos reales
    del repositorio: data/ventas_diarias.csv y data/schemas/transactions_schema.json.
    """

    def test_flujo_completo_con_dataset_real(self) -> None:
        input_csv = Path("data/ventas_diarias.csv")
        schema_json = Path("data/schemas/transactions_schema.json")
        out_report = Path("reports/test_cierre_integration.md")

        # 1. Carga
        raw = DataIngestion.load(input_csv)
        self.assertEqual(len(raw), 20)

        # 2. Validación
        validator = SchemaValidator(schema_json)
        validos, dlq = validator.validate_batch(raw)
        self.assertEqual(len(validos), 19)
        self.assertEqual(len(dlq), 1)

        # 3. Auditoría completa
        result = AuditEngine.run_full_audit(
            transactions=validos,
            monto_declarado=Decimal("3780.50"),
            tolerancia_pct=Decimal("5.0"),
            fecha_auditoria=datetime(2026, 9, 7),
            ruta_reporte=out_report,
            dlq_records=dlq,
        )

        self.assertEqual(result.estado, EstadoAuditoria.BALANCE_OK)
        self.assertEqual(result.balance.balance_neto, Decimal("3780.50"))
        self.assertEqual(len(result.duplicados), 3)

        # 4. Generación de reporte
        content = ReportGenerator.generate(result)
        self.assertIn("title: \"Dictamen de Auditoría Operativa", content)
        self.assertIn("S/ 3,780.50", content)
        self.assertIn("BALANCE_OK", content)


if __name__ == "__main__":
    unittest.main()
