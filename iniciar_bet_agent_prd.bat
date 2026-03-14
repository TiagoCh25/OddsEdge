@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0bet_agent"
if errorlevel 1 (
  echo [ERRO] Nao foi possivel acessar a pasta bet_agent.
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python nao encontrado no PATH.
  exit /b 1
)

if not defined APP_ENV set "APP_ENV=prd"

rem Carrega variaveis por perfil de producao.
call :load_env_file ".env.%APP_ENV%"
call :load_env_file ".env"

if not defined USE_SAMPLE_DATA set "USE_SAMPLE_DATA=false"
if not defined REQUESTS_TRUST_ENV set "REQUESTS_TRUST_ENV=false"
if not defined API_FOOTBALL_AUTH_MODE set "API_FOOTBALL_AUTH_MODE=apisports"
if not defined SERVER_HOST set "SERVER_HOST=0.0.0.0"
if not defined ENABLE_IDLE_SHUTDOWN set "ENABLE_IDLE_SHUTDOWN=false"
if not defined ODDS_ONLY_ACTIVE_SPORTS set "ODDS_ONLY_ACTIVE_SPORTS=true"
if not defined ODDS_MAX_SPORTS_PER_RUN set "ODDS_MAX_SPORTS_PER_RUN=2"
if not defined ODDS_SPORTS set "ODDS_SPORTS=soccer_italy_serie_a,soccer_spain_la_liga,soccer_epl,soccer_brazil_campeonato"

if not defined API_FOOTBALL_KEY echo [AVISO] API_FOOTBALL_KEY nao definida.
if not defined THE_ODDS_API_KEY echo [AVISO] THE_ODDS_API_KEY nao definida.

echo APP_ENV=%APP_ENV%
echo ENABLE_IDLE_SHUTDOWN=%ENABLE_IDLE_SHUTDOWN%
if defined PORT (
  echo Porta via provedor: %PORT%
) else (
  if not defined SERVER_PORT set "SERVER_PORT=8000"
  echo Porta local: %SERVER_PORT%
)

python -B main.py
exit /b %ERRORLEVEL%

:load_env_file
set "_env_file=%~1"
if not exist "%_env_file%" goto :eof
for /f "usebackq tokens=1,* delims==" %%A in ("%_env_file%") do (
  set "_k=%%A"
  set "_v=%%B"
  if defined _k (
    set "_k=!_k: =!"
    if not "!_k!"=="" if /i not "!_k:~0,1!"=="#" set "!_k!=!_v!"
  )
)
goto :eof
