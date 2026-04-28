#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Веб-интерфейс v6 - CoT Reasoning + KB Fallback

Запускается на порту 5006
Активная версия: web_app_v6_cot_fallback.py
"""

import sys
from pathlib import Path

# Импортируем и запускаем приложение из web_app_v6_cot_fallback.py
from v6.web_app_v6_cot_fallback import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006, debug=False)
