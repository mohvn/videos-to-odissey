# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para criar odysee_upload.exe
# Executar em Windows: pyinstaller odysee_upload.spec

block_cipher = None

a = Analysis(
    ['odysee_login.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'selenium',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='odysee_upload',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Janela de consola para ver o progresso
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
