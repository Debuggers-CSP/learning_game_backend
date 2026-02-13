from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import tempfile
import os

app = Flask(__name__)
CORS(app, supports_credentials=True, origins="*")


def _run_code(code: str) -> str:
    if not code.strip():
        return "No code provided."
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp:
        tmp.write(code.encode())
        tmp.flush()
        try:
            result = subprocess.run(
                ["python3", tmp.name],
                capture_output=True,
                text=True,
                timeout=5,
                cwd="/tmp",
                env={"HOME": "/tmp", "PATH": "/usr/bin:/usr/local/bin"}
            )
            return (result.stdout or "") + (result.stderr or "")
        except subprocess.TimeoutExpired:
            return "Execution timed out (5 s limit)."
        except Exception as exc:
            return f"Error running code: {str(exc)}"
        finally:
            os.unlink(tmp.name)


@app.get("/health")
def health_check():
    return jsonify({"ok": True})


@app.post("/run/python")
def run_python():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    output = _run_code(code)
    return jsonify({"output": output})


if __name__ == "__main__":
    port = int(os.environ.get("PYTHON_RUNNER_PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=False)
