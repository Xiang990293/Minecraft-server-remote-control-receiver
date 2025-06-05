#!/bin/bash

python -m venv venv

if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
    echo "偵測到類 Unix 系統, 正在安裝對應 venv..."
    source venv/bin/activate
    pip install -r requirements.txt
    pyinstaller --onefile main.py --distpath .
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    echo "偵測到類 Windows 系統, 正在安裝對應 venv..."
    echo "venv\\Scripts\\activate.bat"
    pip install -r requirements.txt
    pyinstaller --onefile main.py --distpath .
else
    echo "未知的作業系統, 請自行建立虛擬環境並安裝依賴。"
fi
