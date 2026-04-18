#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Веб-интерфейс v6 - CoT Reasoning + KB Fallback

Запускается на порту 5006
Активная версия: web_app_v6_cot_fallback.py
"""

import subprocess
import sys
from pathlib import Path

# Запускаем версию v6 с CoT Reasoning через subprocess
target_file = Path(__file__).parent / 'web_app_v6_cot_fallback.py'
subprocess.run([sys.executable, str(target_file)])
