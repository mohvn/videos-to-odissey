@echo off
REM Build do odysee_upload.exe - executar em Windows
REM Requer: Python 3.10+, pip install -r requirements.txt -r requirements-build.txt

echo [*] A instalar dependencias de build...
pip install -r requirements.txt -r requirements-build.txt -q

echo [*] A construir odysee_upload.exe...
pyinstaller --noconfirm odysee_upload.spec

if exist "dist\odysee_upload.exe" (
    copy /Y "Rodar_Upload.bat" "dist\" >nul 2>&1
    copy /Y "INSTRUCOES_UTILIZADOR.txt" "dist\" >nul 2>&1
    copy /Y ".env.example" "dist\" >nul 2>&1
    echo.
    echo [OK] Executavel criado em: dist\
    echo.
    echo Conteudo da pasta dist\ (pronto a distribuir):
    echo   - odysee_upload.exe
    echo   - Rodar_Upload.bat
    echo   - INSTRUCOES_UTILIZADOR.txt
    echo   - .env.example (renomear para .env e preencher)
    echo.
    echo O utilizador deve adicionar: .env, thumb.jpg e pasta videos\
) else (
    echo [ERRO] Build falhou.
    exit /b 1
)
