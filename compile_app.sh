#!/bin/bash

source venv/bin/activate
pip freeze > requirements.txt
pyinstaller --onefile main.py --distpath .
