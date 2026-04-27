#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Веб-интерфейс v6 - CoT Reasoning + KB Fallback

Запускается на порту 5006
Активная версия: web_app_v6_cot_fallback.py
"""

import sys
from pathlib import Path

# Add the directory containing web_app_v6_cot_fallback.py to the search path
sys.path.append(str(Path(__file__).parent))

# Import the app object from the analyzer module
from web_app_v6_cot_fallback import app

if __name__ == "__main__":
    # Start the server using the imported app
    app.run(host='127.0.0.1', port=5006, debug=False)
