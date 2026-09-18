@echo off
title Eco Smart - excluir usuario
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)

%PY% --version >nul 2>nul
if errorlevel 1 (
    echo ERRO: o Python nao foi encontrado nesta maquina.
    goto fim
)

%PY% excluir_usuario.py

:fim
echo.
pause
