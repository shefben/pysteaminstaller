@echo off
REM Build the installer in one-file mode
REM Build the pywin32-based installer
pyinstaller --noconfirm --onefile --name beta1installer --strip --add-binary "steam.exe;." beta1installer.py

REM Further compress the executable using UPX if it is installed
if exist "dist\beta1installer.exe" (
    upx --best --lzma "dist\beta1installer.exe"
)
