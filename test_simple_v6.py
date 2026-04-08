#!/usr/bin/env python3
"""Простой тест V6"""

import sys
sys.path.insert(0, '/home/segun/CascadeProjects/Перед 0_2/.kilo/worktrees/playful-flower')

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import fitz

app = Flask(__name__)

from web_app_v6_cot_fallback import DocumentAnalyzer

analyzer = DocumentAnalyzer()

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html>
<head><title>V6 Simple Test</title></head>
<body style="font-family: Arial; padding: 20px; background: #1a1a2e; color: #fff;">
    <h1>🧪 V6 Simple Test Server</h1>
    <p>KB loaded: {} entries</p>
    <form action="/analyze" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".pdf,.docx,.xml" style="padding: 10px;">
        <button type="submit" style="padding: 10px 20px; background: #667eea; color: white; border: none; cursor: pointer;">Analyze</button>
    </form>
</body>
</html>
'''.format(len(analyzer.kb_data))

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'})
    
    temp_path = Path('/tmp') / secure_filename(file.filename)
    file.save(temp_path)
    
    try:
        result = analyzer.analyze_pdf(temp_path, file.filename)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        if temp_path.exists():
            temp_path.unlink()

if __name__ == '__main__':
    print("🚀 V6 Simple Test Server")
    print("📍 http://172.31.130.149:5007")
    app.run(host='0.0.0.0', port=5007, debug=False, threaded=True)
