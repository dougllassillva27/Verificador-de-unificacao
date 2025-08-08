@echo off
title Gerador de Executável para o Analisador

:: Muda o diretório de execução para a pasta onde este arquivo .bat está localizado.
cd /d "%~dp0"

echo ==================================================
echo   GERADOR DE EXECUTAVEL - ANALISADOR DE UNIFICACAO
echo ==================================================
echo.

echo --- 1. Atualizando o PIP (Boa pratica)...
python -m pip install --upgrade pip
echo.

echo --- 2. Instalando dependencias do requirements.txt...
python -m pip install -r requirements.txt
echo.

echo --- 3. Instalando o PyInstaller (caso nao esteja instalado)...
python -m pip install pyinstaller
echo.

echo --- 4. Gerando o executavel...
:: *** A CORREÇÃO ESTÁ AQUI ***
:: Chamando o pyinstaller diretamente em vez de "python -m pyinstaller"
pyinstaller --name "AnalisadorDeUnificacao" --onefile --windowed --icon="icone.ico" analise_gui.py

echo.
echo ==================================================
echo   PROCESSO FINALIZADO!
echo.
echo   O arquivo "AnalisadorDeUnificacao.exe" esta na pasta "dist".
echo ==================================================
pause