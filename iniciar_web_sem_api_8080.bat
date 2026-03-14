@echo off
setlocal EnableExtensions

cd /d "%~dp0bet_agent"
if errorlevel 1 (
  echo [ERRO] Nao foi possivel acessar a pasta bet_agent.
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python nao encontrado no PATH.
  pause
  exit /b 1
)

set "APP_ENV=local"
set "SKIP_PIPELINE_ON_START=true"
set "SERVER_HOST=0.0.0.0"
set "SERVER_PORT=8080"
set "ENABLE_IDLE_SHUTDOWN=false"

echo Modo WEB-ONLY ativo ^(sem consumir APIs^).
echo Iniciando em http://localhost:%SERVER_PORT%
start "" http://localhost:%SERVER_PORT%
python -B main.py

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Aplicacao encerrada. Codigo: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
