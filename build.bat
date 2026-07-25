@echo off
chcp 65001 >nul
title Claw's Trainer — 一键构建

:: ============================================================
:: Claw's Trainer — 《侠客风云传前传》修改器 一键构建脚本
:: ============================================================
::
:: 使用方法：双击运行即可
:: 前置条件：已安装 Python 3.7+
::
:: 构建产物：dist\ClawTrainer.exe（单文件，双击直接运行）
:: ============================================================

setlocal enabledelayedexpansion

:: ── 获取脚本所在目录 ──────────────────────────────────────────────
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ╔══════════════════════════════════════════════════╗
echo ║      Claw's Trainer — 一键构建工具               ║
echo ║      《侠客风云传前传》修改器                      ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo [1/5] 检测 Python 环境...

:: 检测 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python！请先安装 Python 3.7+
    echo    下载地址: https://www.python.org/downloads/
    echo.
    echo    安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

python --version
echo.

:: ── 第2步：升级 pip 并安装 PyInstaller ──────────────────────────────
echo [2/5] 安装/更新 PyInstaller...
python -m pip install --upgrade pip -q
python -m pip install pyinstaller -q

if %errorlevel% neq 0 (
    echo ❌ PyInstaller 安装失败！
    pause
    exit /b 1
)
echo ✅ PyInstaller 就绪
echo.

:: ── 第3步：安装运行时依赖 ──────────────────────────────────────────
echo [3/5] 安装运行时依赖 (pymem, psutil)...
python -m pip install pymem psutil -q

if %errorlevel% neq 0 (
    echo ⚠️  依赖安装有警告，继续构建...
)
echo ✅ 依赖就绪
echo.

:: ── 第4步：构建 .exe ──────────────────────────────────────────────
echo [4/5] 开始构建可执行文件...
echo.
echo     输出模式：单文件 + 无控制台窗口
echo     压缩：UPX 启用
echo.

:: 清理旧的构建目录
if exist "dist\ClawTrainer" rmdir /s /q "dist\ClawTrainer" >nul 2>nul
if exist "build" rmdir /s /q "build" >nul 2>nul
if exist "ClawTrainer.spec" del "ClawTrainer.spec" >nul 2>nul

:: 检查是否有图标文件
set "ICON_ARG="
if exist "icon.ico" set "ICON_ARG=--icon=icon.ico"

:: 执行 PyInstaller（使用 spec 文件）
pyinstaller trainer.spec --clean --noconfirm

if %errorlevel% neq 0 (
    echo.
    echo ❌ 构建失败！
    echo    可能原因：
    echo    1. 缺少 Visual C++ 运行时（安装 vc_redist.x86.exe）
    echo    2. 杀毒软件拦截（暂时关闭后重试）
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ 构建完成！
echo.

:: ── 第5步：输出结果 ──────────────────────────────────────────────
echo [5/5] 整理构建产物...

:: 计算文件大小
set "EXE_PATH=dist\ClawTrainer.exe"
if exist "%EXE_PATH%" (
    for %%F in ("%EXE_PATH%") do set "FILE_SIZE=%%~zF"
    set /a "FILE_SIZE_MB=!FILE_SIZE! / 1048576"
    set /a "FILE_SIZE_REM=!FILE_SIZE! %% 1048576 * 100 / 1048576"
    echo ╔══════════════════════════════════════════════════╗
    echo ║              构建成功！                           ║
    echo ╠══════════════════════════════════════════════════╣
    echo ║  文件：!EXE_PATH!
    echo ║  大小：!FILE_SIZE_MB!.!FILE_SIZE_REM! MB
    echo ║  类型：单文件便携版（无需安装 Python）
    echo ╚══════════════════════════════════════════════════╝
    echo.
    echo 📌 使用方式：
    echo     1. 确保游戏已启动 (YoungHero.exe)
    echo     2. 双击运行 ClawTrainer.exe
    echo     3. 点击「附加进程」开始修改
    echo.
    echo ⚠️  安全提示：
    echo     - 杀毒软件可能误报（内存修改器通病）
    echo     - 建议添加信任/排除项后使用
    echo     - 仅供单机游戏使用
    echo.
) else (
    echo ❌ 未找到输出文件，请检查构建日志
)

:: 清理临时构建文件
if exist "ClawTrainer.spec" del "ClawTrainer.spec" >nul 2>nul

echo.
pause
