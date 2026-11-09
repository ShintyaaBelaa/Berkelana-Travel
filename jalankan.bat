@echo off
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python tidak ditemukan. Pasang Python terlebih dahulu.
    pause
    exit /b 1
)

python -c "import streamlit" >nul 2>nul
if errorlevel 1 (
    echo Streamlit belum terpasang. Memasang dependensi...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Pemasangan dependensi gagal.
        pause
        exit /b 1
    )
)

echo Menjalankan Sistem Administrasi Travel Berkelana...
streamlit run app.py
pause
