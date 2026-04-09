#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Веб-интерфейс v6 - CoT Reasoning + KB Fallback

Запускается на порту 5006
Активная версия: web_app_v6_cot_fallback.py
"""

import sys
from pathlib import Path

# Запускаем версию v6 с CoT Reasoning
target_file = Path(__file__).parent / 'web_app_v6_cot_fallback.py'
exec(open(target_file).read())
