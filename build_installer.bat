@echo off
pyinstaller --noconfirm --onefile --add-binary "steam.exe;." beta1installer.py
