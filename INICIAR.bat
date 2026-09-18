@echo off
title Eco Smart - servidor do site
cd /d "%~dp0"

echo ============================================================
echo   ECO SMART - ligando o site
echo ============================================================
echo.

REM Descobre como chamar o Python nesta maquina.
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)

%PY% --version >nul 2>nul
if errorlevel 1 goto sem_python

echo [1/2] Verificando o Flask...
%PY% -c "import flask" >nul 2>nul
if errorlevel 1 (
    echo       Instalando o Flask, aguarde...
    %PY% -m pip install flask --quiet --disable-pip-version-check
    if errorlevel 1 goto erro_flask
) else (
    echo       Flask ja esta instalado, ok.
)

if not exist "ecosmart.db" (
    echo [2/2] Criando o banco de dados...
    %PY% init_db.py
) else (
    echo [2/2] Banco de dados ja existe, mantendo os cadastros.
)

echo.
echo ------------------------------------------------------------
echo   Abrindo no navegador:  http://127.0.0.1:5000
echo   Para desligar:         aperte Ctrl + C ou feche esta janela
echo ------------------------------------------------------------
echo.

start "" http://127.0.0.1:5000
%PY% app.py
goto fim

:sem_python
echo.
echo  ERRO: o Python nao foi encontrado nesta maquina.
echo.
echo  Baixe em https://www.python.org/downloads/
echo  IMPORTANTE: marque a caixinha "Add Python to PATH"
echo  na primeira tela do instalador, senao nao funciona.
goto fim

:erro_flask
echo.
echo  ERRO: nao consegui instalar o Flask.
echo  Verifique se o computador esta conectado a internet.
goto fim

:fim
echo.
pause
