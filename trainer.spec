# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Claw's Trainer
《侠客风云传前传》多功能修改器

Build command:
    pyinstaller trainer.spec

Output: dist/ClawTrainer.exe (single file, no console window)
"""

import os
import sys
from pathlib import Path

# ── 项目根目录 ──────────────────────────────────────────────────────
# 注意：PyInstaller 执行 spec 时 __file__ 不可用，用 os.getcwd()
PROJECT_DIR = Path(os.getcwd())

# ── 图标文件 ─────────────────────────────────────────────────────────
# 如果没有图标文件，此设置会被忽略
ICON_FILE = str(PROJECT_DIR / "icon.ico")
if not os.path.exists(ICON_FILE):
    # Windows 用内置默认图标，macOS 用系统图标
    ICON_FILE = None

# ── PyInstaller Block ────────────────────────────────────────────────
a = Analysis(
    [str(PROJECT_DIR / "main.py")],       # 入口脚本
    pathex=[str(PROJECT_DIR)],              # Python 搜索路径
    binaries=[],                            # 外部二进制文件
    datas=[],                               # 附加数据文件
    hiddenimports=[
        # pymem 及其依赖
        "pymem",
        "pymem.ressources",
        "pymem.ressources.structure",
        "pymem.process",
        "pymem.memory",
        "pymem.pattern",
        # psutil
        "psutil",
        # tkinter 相关
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "tkinter.filedialog",
        "tkinter.scrolledtext",
        # struct (用于值类型转换)
        "struct",
        # threading 和 logging 是内置模块，无需显式声明
    ],
    hookspath=[],
    hooksconfig={},
    excludes=[
        # 安全排除：明确的第三方 / 非依赖模块
        "numpy",
        "matplotlib",
        "PIL",
        "cv2",
        "scipy",
        "pandas",
        "selenium",
        "requests",
        "bs4",
        "lxml",
        "cryptography",
        "OpenSSL",
        "setuptools",
        "pip",
        "venv",
        "ensurepip",
    ],
)

# ── 排除 pymem 调试输出 ─────────────────────────────────────────────
a.datas = [d for d in a.datas if 'pymem.logger' not in str(d[1])]

# ── 打包选项 ─────────────────────────────────────────────────────────
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ClawTrainer",                    # 输出文件名
    debug=False,                           # 关闭调试模式
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                              # 启用 UPX 压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                         # 无控制台窗口（纯GUI模式）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE,
)
