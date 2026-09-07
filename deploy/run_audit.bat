@echo off
chcp 65001 > nul
title PYME Ops Agent - Auditoria Automatica de Caja

echo =====================================================================
echo           PYME OPS AGENT - SISTEMA PRODUCTIVO DE AUDITORIA
echo =====================================================================
echo.

REM 1. Cambiar al directorio raiz del proyecto
cd /d "%~dp0.."

REM 2. Validar si Python esta instalado y disponible en PATH
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR CRITICO] Python no esta instalado o no se encuentra en el PATH.
    echo.
    echo Por favor instale Python 3.10 o superior desde:
    echo   https://www.python.org/downloads/
    echo Asegurese de marcar la casilla "Add python.exe to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

REM 3. Mostrar entorno validado
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VER=%%i
echo [ENTORNO] Entorno validado: %PYTHON_VER%
echo [INICIO]  Iniciando auditoria de ventas del dia...
echo.

REM 4. Ejecutar el motor de auditoria
python tools\audit_engine.py --input data\ventas_diarias.csv --schema data\schemas\transactions_schema.json --output reports\cierre_diario_actual.md --tolerance 5.0
set AUDIT_EXIT_CODE=%ERRORLEVEL%
echo.

REM 5. Evaluar codigo de salida mediante saltos limpios
if %AUDIT_EXIT_CODE% equ 0 goto :res_ok
if %AUDIT_EXIT_CODE% equ 1 goto :res_warn
goto :res_err

:res_ok
echo =====================================================================
echo  [VEREDICTO] AUDITORIA COMPLETADA CON EXITO: BALANCE CONFORME [OK]
echo =====================================================================
echo  El balance de transacciones cuadra con las directrices operativas.
goto :after_eval

:res_warn
echo =====================================================================
echo  [ALERTA] AUDITORIA CONCLUIDA: SE DETECTARON DISCREPANCIAS O ANOMALIAS
echo =====================================================================
echo  Se encontraron descuadres superiores al umbral o duplicados.
echo  Revise detalladamente el reporte generado.
goto :after_eval

:res_err
echo =====================================================================
echo  [ERROR] OCURRIO UN ERROR TECNICO [Codigo %AUDIT_EXIT_CODE%]
echo =====================================================================

:after_eval
echo.
echo [REPORTE] Abriendo el dictamen ejecutivo generado...
if exist "reports\cierre_diario_actual.md" (
    start "" "reports\cierre_diario_actual.md"
) else (
    echo [AVISO] No se encontro el archivo de reporte.
)

echo.
echo Presione cualquier tecla para cerrar esta ventana...
pause > nul
exit /b %AUDIT_EXIT_CODE%
