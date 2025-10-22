@echo off
REM Start the Observability API server on Windows

REM Get script directory
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Change to project root
cd /d "%PROJECT_ROOT%"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install dependencies if needed
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r src\observability\requirements.txt
)

REM Parse command line arguments
set DEV_MODE=
set WORKERS=4
set HOST=127.0.0.1
set PORT=8000

:parse_args
if "%1"=="" goto end_parse
if "%1"=="--dev" (
    set DEV_MODE=--dev
    shift
    goto parse_args
)
if "%1"=="--workers" (
    set WORKERS=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--host" (
    set HOST=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--port" (
    set PORT=%2
    shift
    shift
    goto parse_args
)
shift
goto parse_args

:end_parse

REM Start the server
echo Starting Observability API...
echo   Host: %HOST%
echo   Port: %PORT%

if defined DEV_MODE (
    echo   Mode: Development (auto-reload enabled)
    python src\observability\server.py --dev --host %HOST% --port %PORT% --log-level DEBUG
) else (
    echo   Mode: Production
    echo   Workers: %WORKERS%
    python src\observability\server.py --host %HOST% --port %PORT% --workers %WORKERS% --log-level INFO
)
