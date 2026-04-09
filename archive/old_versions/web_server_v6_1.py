#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Веб-интерфейс v6.1 - с индикатором KB override"""

import sys
import json
from pathlib import Path
from datetime import datetime
from io import BytesIO

from flask import Flask, request, render_template_string, jsonify
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).parent / '.kilo/worktrees/playful-flower'))
from web_app_v5_final import DocumentAnalyzer

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'

Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)

analyzer = DocumentAnalyzer(use_llm=True)

HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Document Analyzer v6.1</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:#1a1a2e;color:#e0e0e0;padding:20px}
.container{max-width:1200px;margin:0 auto}
h1{text-align:center;color:#667eea;margin-bottom:10px}
.subtitle{text-align:center;color:#888;margin-bottom:30px}
.upload-zone{background:#24243e;padding:30px;border-radius:20px;text-align:center;margin-bottom:20px}
.file-input{padding:12px;border:2px dashed #667eea;border-radius:10px;color:#aaa;width:100%;max-width:400px}
.upload-btn{background:#667eea;color:white;padding:12px 30px;border:none;border-radius:25px;margin-top:15px;cursor:pointer;font-weight:600}
.upload-btn:disabled{opacity:0.5}
.file-name{color:#667eea;margin-top:10px}

.kb-box{background:#24243e;border-radius:15px;padding:20px;margin-bottom:20px;display:none}
.kb-row{display:flex;align-items:center;gap:15px;margin-bottom:10px}
.kb-badge{padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600}
.kb-badge.ok{background:#10b981;color:white}
.kb-badge.warn{background:#f59e0b;color:white}
.kb-badge.no{background:#ef4444;color:white}
.kb-score{font-size:28px;font-weight:700;color:#667eea}
.kb-title{color:#888;font-size:13px}
.kb-examples{background:#1a1a2e;padding:15px;border-radius:10px;margin-top:15px}
.kb-examples h4{color:#667eea;margin-bottom:10px}
.ex-item{background:#2d2d44;padding:10px;border-radius:8px;margin-bottom:8px;font-size:13px}

.result{background:#24243e;border-radius:20px;padding:30px;display:none}
table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{padding:12px;text-align:left;border-bottom:1px solid #2d2d44}
th{background:#667eea;color:white;font-weight:600}
td:first-child{color:#667eea;width:200px}

.loading{text-align:center;padding:40px;display:none}
.spinner{border:4px solid #2d2d44;border-top:4px solid #667eea;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin:0 auto 15px}
@keyframes spin{to{transform:rotate(360deg)}}

.actions{margin-top:20px;display:flex;gap:10px}
.btn{padding:10px 20px;border:none;border-radius:8px;cursor:pointer;font-weight:600}
.btn-dl{background:#10b981;color:white}
.btn-copy{background:#3b82f6;color:white}
.btn-clear{background:#6b7280;color:white}

.error{background:#ef4444;color:white;padding:15px;border-radius:10px;margin-top:20px;display:none}
</style>
</head>
<body>
<div class="container">
<h1>📄 Document Analyzer v6.1</h1>
<p class="subtitle">Mistral 14B + Knowledge Base с визуализацией matching</p>

<div class="upload-zone">
    <input type="file" id="fileInput" accept=".pdf,.docx,.xml" class="file-input">
    <div id="fileName" class="file-name"></div>
    <button id="submitBtn" class="upload-btn" disabled>🔍 Анализировать</button>
</div>

<div class="loading" id="loading">
    <div class="spinner"></div>
    <div>Анализирую документ...</div>
</div>

<div class="error" id="error"></div>

<div class="kb-box" id="kbBox">
    <div class="kb-row">
        <span class="kb-badge" id="kbBadge">—</span>
        <span class="kb-score" id="kbScore">0%</span>
    </div>
    <div class="kb-title" id="kbTitle">—</div>
    <div class="kb-examples" id="kbExamples">
        <h4>📊 Примеры для LLM:</h4>
        <div id="examplesList"></div>
    </div>
</div>

<div class="result" id="result">
    <h2 id="resultTitle">—</h2>
    <table><tbody id="tbody"></tbody></table>
    <div class="actions">
        <button class="btn btn-dl" onclick="downloadJSON()">📥 JSON</button>
        <button class="btn btn-copy" onclick="copyJSON()">📋 Копировать</button>
        <button class="btn btn-clear" onclick="clear()">🗑️ Очистить</button>
    </div>
</div>
</div>

<script>
let currentResult = null;

document.getElementById('fileInput').addEventListener('change', e => {
    const f = e.target.files[0];
    document.getElementById('fileName').textContent = f ? '📄 ' + f.name : '';
    document.getElementById('submitBtn').disabled = !f;
});

document.getElementById('submitBtn').addEventListener('click', () => {
    const fileInput = document.getElementById('fileInput');
    if (!fileInput.files[0]) return;
    
    document.getElementById('loading').style.display = 'block';
    document.getElementById('result').style.display = 'none';
    document.getElementById('kbBox').style.display = 'none';
    document.getElementById('error').style.display = 'none';
    
    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    
    fetch('/analyze', {method:'POST', body:fd})
    .then(r => r.json())
    .then(data => {
        document.getElementById('loading').style.display = 'none';
        if (data.error) {
            document.getElementById('error').textContent = data.error;
            document.getElementById('error').style.display = 'block';
        } else {
            currentResult = data;
            showResult(data);
        }
    })
    .catch(err => {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error').textContent = err.message;
        document.getElementById('error').style.display = 'block';
    });
});

function showResult(d) {
    document.getElementById('resultTitle').textContent = d.filename;
    
    // KB indicator
    if (d.kb_match) {
        const score = d.kb_match.score;
        const badge = document.getElementById('kbBadge');
        
        if (score >= 90) {
            badge.className = 'kb-badge ok';
            badge.textContent = '✓ KB Override';
        } else if (score >= 60) {
            badge.className = 'kb-badge warn';
            badge.textContent = '⚠ KB Match';
        } else {
            badge.className = 'kb-badge no';
            badge.textContent = '✗ Regex';
        }
        
        document.getElementById('kbScore').textContent = score + '%';
        document.getElementById('kbTitle').textContent = 'Найдено: "' + d.kb_match.title + '"';
        
        // Examples
        if (d.kb_examples) {
            const list = document.getElementById('examplesList');
            list.innerHTML = '';
            d.kb_examples.forEach((ex, i) => {
                const div = document.createElement('div');
                div.className = 'ex-item';
                div.textContent = (i+1) + '. ' + ex.title + ' (' + ex.score + '%)';
                list.appendChild(div);
            });
        }
        
        document.getElementById('kbBox').style.display = 'block';
    }
    
    // Table
    const tbody = document.getElementById('tbody');
    tbody.innerHTML = '';
    
    [
        ['Название', d.title],
        ['Заказчик', d.customer],
        ['Разработчик', d.developer],
        ['Год', d.year],
        ['Тип', d.document_type],
        ['Содержимое', d.content_summary],
        ['Цель', d.purpose]
    ].forEach(([k, v]) => {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td>' + k + '</td><td>' + (v || '—') + '</td>';
        tbody.appendChild(tr);
    });
    
    document.getElementById('result').style.display = 'block';
}

function downloadJSON() {
    if (!currentResult) return;
    const blob = new Blob([JSON.stringify(currentResult, null, 2)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'analysis.json';
    a.click();
}

function copyJSON() {
    if (!currentResult) return;
    navigator.clipboard.writeText(JSON.stringify(currentResult, null, 2));
    alert('Скопировано!');
}

function clear() {
    document.getElementById('result').style.display = 'none';
    document.getElementById('kbBox').style.display = 'none';
    document.getElementById('fileInput').value = '';
    document.getElementById('fileName').textContent = '';
    document.getElementById('submitBtn').disabled = true;
    currentResult = null;
}
</script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/analyze', methods=['POST'])
def analyze_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Нет файла'})
    
    f = request.files['file']
    if f.filename == '':
        return jsonify({'error': 'Файл не выбран'})
    
    filename = f.filename
    suffix = Path(filename).suffix.lower()
    
    temp = Path(app.config['UPLOAD_FOLDER']) / secure_filename(filename)
    f.save(temp)
    
    try:
        if suffix == '.pdf':
            result = analyzer.analyze_pdf(temp, filename)
        elif suffix in ('.docx', '.doc'):
            result = analyzer.analyze_docx(temp, filename)
        elif suffix == '.xml':
            result = analyzer.analyze_xml(temp, filename)
        else:
            result = {'error': 'Неподдерживаемый формат'}
        
        # Add KB info
        matching = analyzer._get_kb_matching_entries(filename, top_n=3)
        if matching:
            score, best = matching[0]
            result['kb_match'] = {'score': int(score * 100), 'title': best.get('title', '')[:60]}
            result['kb_examples'] = [{'title': e.get('title','')[:50], 'score': int(s*100)} for s,e in matching[:2]]
        
        result['filename'] = filename
    except Exception as e:
        result = {'error': str(e)}
    finally:
        if temp.exists(): temp.unlink()
    
    return jsonify(result)

if __name__ == '__main__':
    print("=" * 60)
    print("🌐 Document Analyzer v6.1: http://localhost:5005")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5005, debug=False)
