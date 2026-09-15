from flask import Flask, render_template, request, jsonify, Response
import os
import json
import random
import string
import re

app = Flask(__name__)

DB_FILE = "scripts_db.json"


def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)


SCRIPTS = load_db()


def random_id(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


# Anti-tamper nhe, khong gay lag
ANTI_TAMPER_LIGHT = """if not game or not game.GetService then return end
local _ok = pcall(function() return game:GetService("Players") end)
if not _ok then return end
"""


def minify_lua(code):
    """Nen Lua code manh."""
    code = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
    code = re.sub(r'--[^\n]*', '', code)
    code = re.sub(r'\s+', ' ', code)
    code = re.sub(r'\s*([=+\-*/%^,;(){}[\]])\s*', r'\1', code)
    return code.strip()


def obfuscate_lua(code, options):
    """Obfuscate toi uu, khong gay lag."""
    output = code

    if options.get('minify', True):
        output = minify_lua(output)

    if options.get('antiTamper', True):
        output = ANTI_TAMPER_LIGHT + output

    if options.get('wrapLoadstring', True):
        escaped = output.replace('\\', '\\\\').replace('"', '\\"')
        escaped = escaped.replace('\n', '\\n').replace('\r', '')
        output = 'loadstring("' + escaped + '")()'

    return output


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/obfuscate", methods=["POST"])
def api_obfuscate():
    try:
        data = request.get_json()
        code = data.get("code", "").strip()
        options = data.get("options", {})

        if not code:
            return jsonify({"ok": False, "error": "Vui long nhap code!"})

        output = obfuscate_lua(code, options)
        script_id = random_id()
        SCRIPTS[script_id] = output
        save_db(SCRIPTS)

        base_url = request.host_url.rstrip('/')
        raw_url = base_url + "/raw/" + script_id
        loadstring_code = 'loadstring(game:HttpGet("' + raw_url + '"))()'

        return jsonify({
            "ok": True,
            "output": output,
            "raw_url": raw_url,
            "loadstring": loadstring_code,
            "size": len(output)
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/raw/<script_id>")
def raw_script(script_id):
    if script_id not in SCRIPTS:
        return "Script khong ton tai.", 404

    code = SCRIPTS[script_id]
    user_agent = request.headers.get('User-Agent', '').lower()
    executor_keywords = ['roblox', 'delta', 'executor', 'synapse', 'krnl',
                         'fluxus', 'evon', 'codex', 'httpget', 'wave', 'solara',
                         'xeno', 'hydrogen', 'argon']
    is_executor = any(kw in user_agent for kw in executor_keywords)

    if not is_executor:
        return render_template("protected.html"), 200

    return Response(code, mimetype='text/plain')


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
