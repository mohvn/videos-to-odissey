@echo off
REM Duplo-clique para enviar videos para o Odysee
REM Coloque os videos na pasta "videos" e o thumb.jpg nesta pasta

cd /d "%~dp0"

if not exist "odysee_upload.exe" (
    echo ERRO: odysee_upload.exe nao encontrado.
    echo Coloque este ficheiro na mesma pasta que o executavel.
    pause
    exit /b 1
)

if not exist ".env" (
    echo ERRO: Ficheiro .env nao encontrado.
    echo Crie um ficheiro .env com:
    echo   ODYSEE_EMAIL=seu@email.com
    echo   ODYSEE_PASSWORD=sua_senha
    pause
    exit /b 1
)

odysee_upload.exe --upload --no-headless

echo.
pause
