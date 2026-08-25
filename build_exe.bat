@echo off
chcp 65001 >nul
title Đóng Gói TS Origin Control sang file EXE
echo ============================================================
echo   ĐANG TIẾN HÀNH ĐÓNG GÓI TS ORIGIN CONTROL SANG FILE .EXE
echo ============================================================
echo.

python -m PyInstaller --noconsole --onefile --name "TS_Origin_Control" --collect-all customtkinter --add-data "assets;assets" main.py

echo.
if exist "dist\TS_Origin_Control.exe" (
    echo 📥 Đang sao chép thư mục assets vào thư mục dist...
    if not exist "dist\assets" mkdir "dist\assets"
    xcopy /E /I /Y "assets" "dist\assets" >nul

    echo 🧹 Đang tự động dọn dẹp các thư mục rác tạm thời...
    if exist "build" rmdir /s /q "build"
    if exist "__pycache__" rmdir /s /q "__pycache__"
    if exist "TS_Origin_Control.spec" del /f /q "TS_Origin_Control.spec"

    echo.
    echo ============================================================
    echo   ✅ ĐÓNG GÓI THÀNH CÔNG!
    echo   📁 File chạy của bạn nằm tại: dist\TS_Origin_Control.exe
    echo ============================================================
) else (
    echo ❌ Đóng gói thất bại. Vui lòng kiểm tra lại log lỗi ở trên.
)
echo.
pause
