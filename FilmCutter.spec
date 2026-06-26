# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：onedir（文件夹）、无控制台窗口、带图标。

入口为 movie_gui.py（真正的应用）。run.py 是热更新开发启动器，不打包。
FFmpeg 不内置 —— 目标机器需自行安装 ffmpeg 并加入 PATH。
"""
import os
import sys

# 本 venv 基于 Anaconda，其运行期 DLL（sqlite3/libcrypto/libssl/libbz2）
# 位于 base_prefix\Library\bin，PyInstaller 默认不搜索该目录，需显式打包，
# 否则打包后 import sqlite3 / hashlib / bz2 会因找不到 DLL 而启动崩溃。
_base = getattr(sys, "base_prefix", "") or os.path.dirname(sys.executable)
_lib_bin = os.path.join(_base, "Library", "bin")
_extra_dlls = ["sqlite3.dll", "libcrypto-3-x64.dll", "libssl-3-x64.dll", "libbz2.dll"]
binaries = [(os.path.join(_lib_bin, n), ".") for n in _extra_dlls
            if os.path.exists(os.path.join(_lib_bin, n))]

block_cipher = None

a = Analysis(
    ['movie_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=[('icon.svg', '.')],          # 只读资源：图标，运行期由 resource_path() 读取
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # 未使用的 Qt 大模块，缩小体积（本程序未用到）
        'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebEngine',
        'PyQt5.QtWebSockets', 'PyQt5.QtNetwork', 'PyQt5.QtSql', 'PyQt5.QtTest',
        'PyQt5.QtMultimedia', 'PyQt5.QtPrintSupport', 'PyQt5.QtBluetooth',
        'PyQt5.QtSerialPort', 'PyQt5.QtPositioning', 'PyQt5.QtLocation',
        'PyQt5.QtSensors', 'PyQt5.QtNfc', 'PyQt5.QtXmlPatterns', 'PyQt5.QtQml',
        'PyQt5.QtQuick', 'PyQt5.QtQuickWidgets', 'PyQt5.QtOpenGL', 'PyQt5.QtDBus',
        'tkinter', 'unittest', 'pydoc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,             # onedir：二进制由 COLLECT 收集
    name='FilmCutter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                     # 窗口程序，不弹黑框
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FilmCutter',
)
