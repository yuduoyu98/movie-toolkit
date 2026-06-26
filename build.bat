@echo off
REM 一键打包 FilmCutter（Windows, onedir 文件夹版）
REM 数据存于 %LOCALAPPDATA%\FilmCutter，独立于 dist —— 重新打包不会丢数据。
REM 依赖：.venv（已装 PyQt5）、系统 PATH 中的 ffmpeg（运行期需要）
chcp 65001 >nul
cd /d "%~dp0"

echo [1/2] 生成 icon.ico ...
".venv\Scripts\python.exe" make_icon.py || goto :error

echo [2/2] PyInstaller 打包 ...
".venv\Scripts\python.exe" -m PyInstaller FilmCutter.spec --noconfirm --clean || goto :error

echo.
echo 完成！产物在 dist\FilmCutter\FilmCutter.exe
echo   - 运行期数据（data.db / 配置 / tmp）写在 %%LOCALAPPDATA%%\FilmCutter\
echo     （独立于 dist，重新打包/覆盖 dist 不影响数据）
echo   - 目标机器需自行安装 ffmpeg 并加入 PATH
exit /b 0

:error
echo 打包失败。
exit /b 1
