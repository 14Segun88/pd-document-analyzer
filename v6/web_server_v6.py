#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Веб-интерфейс v6 - CoT Reasoning + KB Fallback

Запускается на порту 5006
Активная версия: web_app_v6_cot_fallback.py
"""

import os
from web_app_v6_cot_fallback import app

if __name__ == '__main__':
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", 5006))
    print(f"🚀 Сервер запущен: http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
