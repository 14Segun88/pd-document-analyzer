#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Веб-интерфейс v6 - CoT Reasoning + KB Fallback

Запускается на порту 5006
Активная версия: web_app_v6_cot_fallback.py
"""

import subprocess
from pathlib import Path

if __name__ == "__main__":
    # Запускаем версию v6 с CoT Reasoning через subprocess для безопасности
    target_file = Path(__file__).parent / 'web_app_v6_cot_fallback.py'
    subprocess.run(["python3", str(target_file)])
