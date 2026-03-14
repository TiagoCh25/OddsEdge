@echo off
setlocal EnableExtensions EnableDelayedExpansion

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

if not defined APP_ENV set "APP_ENV=local"

rem Carrega variaveis de ambiente por perfil (sem sobrescrever ambiente ja definido)
call :load_env_file ".env"
call :load_env_file ".env.%APP_ENV%"

rem Launcher padrao: sempre usa dados reais e ignora proxy do sistema.
set "USE_SAMPLE_DATA=false"
if not defined REQUESTS_TRUST_ENV set "REQUESTS_TRUST_ENV=false"
if not defined API_FOOTBALL_AUTH_MODE set "API_FOOTBALL_AUTH_MODE=apisports"
if not defined SERVER_HOST set "SERVER_HOST=0.0.0.0"
if not defined SERVER_PORT set "SERVER_PORT=8000"
if not defined ENABLE_IDLE_SHUTDOWN set "ENABLE_IDLE_SHUTDOWN=true"
if not defined IDLE_SHUTDOWN_SECONDS set "IDLE_SHUTDOWN_SECONDS=25"
if not defined ODDS_ONLY_ACTIVE_SPORTS set "ODDS_ONLY_ACTIVE_SPORTS=true"
if not defined ODDS_MAX_SPORTS_PER_RUN set "ODDS_MAX_SPORTS_PER_RUN=2"
if not defined ODDS_SPORTS set "ODDS_SPORTS=soccer_italy_serie_a,soccer_spain_la_liga,soccer_epl,soccer_brazil_campeonato"

if not defined API_FOOTBALL_KEY (
  for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('API_FOOTBALL_KEY','User')"`) do set "API_FOOTBALL_KEY=%%i"
)
if not defined THE_ODDS_API_KEY (
  for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('THE_ODDS_API_KEY','User')"`) do set "THE_ODDS_API_KEY=%%i"
)

if not defined API_FOOTBALL_KEY echo [AVISO] API_FOOTBALL_KEY nao definida no ambiente. Sera usada a configuracao do codigo.
if not defined THE_ODDS_API_KEY echo [AVISO] THE_ODDS_API_KEY nao definida no ambiente. Sera usada a configuracao do codigo.

for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$ids = Get-NetTCPConnection -LocalPort %SERVER_PORT% -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if($ids){ $ids -join [Environment]::NewLine }"`) do (
  if not "%%P"=="" (
    echo Encerrando processo anterior na porta %SERVER_PORT% ^(PID %%P^)...
    taskkill /PID %%P /F >nul 2>&1
  )
)

:run_app
echo Projeto em execucao: %cd%
echo Iniciando Bet Agent na porta %SERVER_PORT%...
echo Aguardando dados de hoje para abrir o navegador...
start "" powershell -NoProfile -Command "$port='%SERVER_PORT%'; $api='http://localhost:' + $port + '/bets'; $url='http://localhost:' + $port; $opened=$false; $deadline=(Get-Date).AddMinutes(3); while((Get-Date) -lt $deadline){ try { $resp = Invoke-RestMethod -Uri $api -TimeoutSec 4; $gen = $resp.generated_at; if($gen){ $genDate = ([datetime]$gen).ToString('yyyy-MM-dd'); $today = (Get-Date).ToString('yyyy-MM-dd'); if($genDate -eq $today){ Start-Process $url; $opened=$true; break } } } catch {} ; Start-Sleep -Seconds 2 }; if(-not $opened){ Start-Process $url }"
echo Esta janela permanecera aberta enquanto o servidor estiver em execucao.
python -B main.py

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Aplicacao encerrada. Codigo: %EXIT_CODE%
pause
exit /b %EXIT_CODE%

:load_env_file
set "_env_file=%~1"
if not exist "%_env_file%" goto :eof
for /f "usebackq tokens=1,* delims==" %%A in ("%_env_file%") do (
  set "_k=%%A"
  set "_v=%%B"
  call :normalize_value _k
  call :normalize_value _v
  if defined _k (
    if not "!_k!"=="" if /i not "!_k:~0,1!"=="#" set "!_k!=!_v!"
  )
)
goto :eof

:normalize_value
set "_name=%~1"
if not defined _name goto :eof
call set "_raw=%%%_name%%%"
if not defined _raw (
  set "%_name%="
  goto :eof
)
for /f "tokens=* delims= " %%Z in ("!_raw!") do set "_raw=%%Z"
:trim_tail
if not defined _raw goto :after_trim_tail
if "!_raw:~-1!"==" " (
  set "_raw=!_raw:~0,-1!"
  goto :trim_tail
)
:after_trim_tail
if "!_raw:~0,1!"=="^"" if "!_raw:~-1!"=="^"" set "_raw=!_raw:~1,-1!"
if "!_raw:~0,1!"=="'" if "!_raw:~-1!"=="'" set "_raw=!_raw:~1,-1!"
set "%_name%=%_raw%"
goto :eof
