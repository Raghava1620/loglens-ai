from flask import Flask, request, jsonify
import urllib.request
import urllib.error
import json
import os
import re

API_KEY = "YOUR_API_KEY_HERE"

app = Flask(__name__)

@app.route('/')
def index():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'loglens_ui.html'), encoding='utf-8') as f:
        return f.read()

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    log = data.get('log', '')
    log_type = data.get('logType', 'auto')
    focus = data.get('focus', 'all')

    prompt = (
        "You are LogLens AI. Analyze this log file.\n"
        "Respond with ONLY a valid JSON object. No explanation, no markdown, no backticks.\n"
        "Use this exact structure:\n"
        '{"health_score":75,"health_title":"Some Issues Detected",'
        '"critical_count":1,"warning_count":2,"info_count":1,'
        '"anomalies":[{"severity":"critical","title":"Issue title",'
        '"description":"What went wrong in plain English.",'
        '"line":"the actual log line here","impact":"Effect on system"}],'
        '"root_cause":"Why this happened. Plain English. 2-3 sentences.",'
        '"suggested_fixes":["Fix step 1","Fix step 2","Fix step 3","Fix step 4"],'
        '"summary":"3-4 sentence summary of what happened and what to do."}\n\n'
        "IMPORTANT: Your entire response must be valid JSON only. No text before or after.\n"
        "Log type: " + log_type + "\n"
        "Focus: " + focus + "\n"
        "Log to analyze:\n" + log
    )

    try:
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )
        res = urllib.request.urlopen(req)
        result = json.loads(res.read().decode('utf-8'))
        raw = result['content'][0]['text']
        print("RAW RESPONSE:", raw[:200])

        # Try multiple ways to extract JSON
        # Method 1: direct parse
        try:
            parsed = json.loads(raw)
            return jsonify(parsed)
        except:
            pass

        # Method 2: strip markdown fences
        clean = raw.strip()
        if clean.startswith('```'):
            clean = re.sub(r'^```[a-z]*\n?', '', clean)
            clean = re.sub(r'```$', '', clean).strip()
        try:
            parsed = json.loads(clean)
            return jsonify(parsed)
        except:
            pass

        # Method 3: find JSON object in response
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                return jsonify(parsed)
            except:
                pass

        return jsonify({"error": "Could not parse AI response. Raw: " + raw[:200]}), 500

    except urllib.error.HTTPError as e:
        body = e.read()
        print("API ERROR:", body)
        try:
            err = json.loads(body)
            msg = err.get('error', {}).get('message', str(body))
        except:
            msg = body.decode('utf-8', errors='replace')
        return jsonify({"error": msg}), 500
    except Exception as e:
        print("EXCEPTION:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("\nLogLens AI is running!")
    print("Open this in Chrome: http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    app.run(debug=False, port=5000)
