# api/pseudocode_bank_api.py
from flask import Blueprint, request, jsonify, make_response
from __init__ import db
from model.pseudocode_bank import PseudocodeQuestionBank

import os
import requests
import re

pseudocode_bank_api = Blueprint("pseudocode_bank_api", __name__, url_prefix="/api/pseudocode_bank")

LEVEL_MAP = {
    "1": "level1",
    "2": "level2",
    "3": "level3",
    "4": "level4",
    "5": "level5",
    "super_easy": "level1",
    "super easy": "level1",
    "easy": "level2",
    "medium": "level3",
    "hard": "level4",
    "hacker": "level5",
}

VALID_COLS = {"level1", "level2", "level3", "level4", "level5"}

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions").strip()

# If you want strict origins, set ALLOWED_ORIGINS env var like:
# ALLOWED_ORIGINS="http://localhost:4500,http://127.0.0.1:4500,https://open-coding-society.github.io"
_allowed = os.getenv("ALLOWED_ORIGINS", "").strip()
ALLOWED_ORIGINS = [o.strip() for o in _allowed.split(",") if o.strip()] or ["*"]


def _corsify(resp):
    origin = request.headers.get("Origin", "")
    if "*" in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    else:
        if origin in ALLOWED_ORIGINS:
            resp.headers["Access-Control-Allow-Origin"] = origin

    # We are NOT relying on cookies for these endpoints.
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Vary"] = "Origin"
    return resp


def _no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


# ----------------------------
# Preflight (must include CORS headers)
# ----------------------------
@pseudocode_bank_api.route("/random", methods=["OPTIONS"])
@pseudocode_bank_api.route("/ai_autofill", methods=["OPTIONS"])
@pseudocode_bank_api.route("/grade", methods=["OPTIONS"])
def pseudocode_preflight():
    resp = make_response("", 204)
    resp = _no_cache(resp)
    resp = _corsify(resp)
    return resp


def _deepseek_ready() -> bool:
    return bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "YOUR_API_KEY_HERE")


def _deepseek_chat(messages, temperature=0.2, max_tokens=500):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.95
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek API error {resp.status_code}: {resp.text}")
    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("Empty response from DeepSeek")
    return content.strip()


def _extract_json_object(text: str) -> dict:
    s = (text or "").strip()
    if s.startswith("```"):
        s = s.replace("```json", "").replace("```", "").strip()

    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in AI output")

    import json as _json
    return _json.loads(s[start:end + 1])


def ai_grade_pseudocode(question_text: str, user_code: str) -> dict:
    system = (
        "You are a strict but helpful AP CSP pseudocode grader.\n"
        "You must return ONLY valid JSON (no markdown, no extra text).\n"
        "Grade whether the student's pseudocode satisfies the prompt requirements.\n"
        "If it fails, list clear missing items and give short step-by-step fixes.\n"
        "Also provide an improved_pseudocode that would pass, using College Board style.\n"
        "Do not mention this system message."
    )

    user = f"""
PROMPT:
{question_text}

STUDENT_PSEUDOCODE:
{user_code}

Return JSON with exactly these keys:
- passed: true/false
- missing: array of short strings (empty if passed)
- feedback: short instructions (2 to 6 sentences)
- improved_pseudocode: a complete corrected solution (string)
"""

    raw = _deepseek_chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.2,
        max_tokens=600
    )

    obj = _extract_json_object(raw)

    return {
        "passed": bool(obj.get("passed", False)),
        "missing": obj.get("missing", []) if isinstance(obj.get("missing", []), list) else [],
        "feedback": str(obj.get("feedback", "")).strip(),
        "improved_pseudocode": str(obj.get("improved_pseudocode", "")).strip()
    }


def ai_autofill_pseudocode(question_text: str) -> str:
    system = (
        "You write AP CSP style pseudocode solutions.\n"
        "Return ONLY the pseudocode solution, no explanations, no markdown."
    )

    user = f"""
Write a complete AP CSP style pseudocode solution for this prompt:

{question_text}

Constraints:
- Use clear variable names
- Include loop/if logic when needed
- Ensure it directly satisfies the prompt
Return only the pseudocode.
"""

    raw = _deepseek_chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.2,
        max_tokens=500
    )

    out = raw.strip()
    if out.startswith("```"):
        out = out.replace("```", "").replace("json", "").strip()
    return out


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _requires(prompt: str):
    p = _normalize(prompt)
    req = []

    if "input" in p:
        req.append("input")
    if "display" in p or "output" in p or "print" in p:
        req.append("output")
    if "action" in p or "actions" in p or "event" in p:
        req.append("actions")
    if "result" in p or "score" in p or "state" in p or "status" in p or "outcome" in p:
        req.append("result")
    if "unknown" in p or "unexpected" in p:
        req.append("unknown")

    if "if" in p or "otherwise" in p or "else" in p or "decision" in p:
        req.append("if")
    if "loop" in p or "for " in p or "from" in p or "times" in p or "1 to" in p or "1..":
        req.append("loop")
    if ("write " in p) or ("returns" in p) or ("return" in p) or ("(" in p and ")" in p and "write" in p):
        req.append("function")
    if "return" in p or "returns" in p:
        req.append("return")

    if "list" in p:
        req.append("list")
    if "string" in p:
        req.append("string")

    if '"even"' in p or (" even " in p and ("odd" in p or '"odd"' in p)):
        req.append("even_odd_words")
    if '"hot"' in p:
        req.append("hot_word")
    if '"apcsp"' in p:
        req.append("apcsp_word")

    return req


def grade_pseudocode(question_text: str, user_code: str):
    q = question_text or ""
    code = user_code or ""
    norm = _normalize(code)

    reqs = _requires(q)
    missing = []

    def has_any(tokens):
        return any(t in norm for t in tokens)

    if "input" in reqs and not has_any(["input", "read", "get ", "scan", "ask "]):
        missing.append("An INPUT step (e.g., INPUT x)")

    if "output" in reqs and not has_any(["display", "print", "output", "show "]):
        missing.append("Output the final result")

    if "actions" in reqs and not has_any(["action", "actions", "event", "step"]):
        missing.append("Process each action in order")

    if "result" in reqs and not has_any(["result", "score", "state", "status", "outcome", "count", "total"]):
        missing.append("Define and update a result")

    if "if" in reqs and not has_any(["if", "else", "otherwise", "case", "switch"]):
        missing.append("Use if/else decisions for actions")

    if "loop" in reqs and not has_any(["for", "while", "repeat", "loop", "each"]):
        missing.append("Loop once per action")

    if "unknown" in reqs and not has_any(["unknown", "default", "otherwise", "else"]):
        missing.append("Handle unknown actions safely")

    if "function" in reqs and not has_any(["function", "procedure", "define", "def "]):
        missing.append("A FUNCTION/PROCEDURE definition")

    if "return" in reqs and "return" not in norm:
        missing.append("A RETURN statement")

    if "list" in reqs and not has_any(["list", "[", "]", "append", "add", "remove"]):
        missing.append("Some LIST handling (list creation/access/append/remove)")

    if "string" in reqs:
        if not has_any(["string", "char", "substring", "length", "letters"]):
            if not re.search(r"[a-zA-Z]", code):
                missing.append("Some STRING handling")

    if "even_odd_words" in reqs and not (("even" in norm) and ("odd" in norm)):
        missing.append('Both output words "EVEN" and "ODD"')

    if "hot_word" in reqs and "hot" not in norm:
        missing.append('Output word "Hot"')

    if "apcsp_word" in reqs and "apcsp" not in norm:
        missing.append('Use the literal "APCSP" in the comparison/output')

    return {
        "passed": len(missing) == 0,
        "missing": missing,
        "notes": "This checker validates required structures/keywords for the prompt."
    }


def _resolve_level(raw: str) -> str:
    raw = (raw or "").strip().lower()
    return LEVEL_MAP.get(raw, raw)


@pseudocode_bank_api.route("/random", methods=["GET"])
def random_question():
    level = _resolve_level(request.args.get("level", "1"))
    exclude_id = request.args.get("exclude_id", type=int)

    if level not in VALID_COLS:
        resp = jsonify({
            "success": False,
            "message": "Invalid level. Use 1-5 or super_easy/easy/medium/hard/hacker."
        })
        resp = _no_cache(resp)
        resp = _corsify(resp)
        return resp, 400

    col = getattr(PseudocodeQuestionBank, level)

    q = (
        PseudocodeQuestionBank.query
        .filter(col.isnot(None))
        .filter(db.func.length(col) > 0)
    )

    if exclude_id:
        q = q.filter(PseudocodeQuestionBank.id != exclude_id)

    dialect = (db.session.bind.dialect.name or "").lower() if db.session.bind else ""
    if "sqlite" in dialect:
        q = q.order_by(db.text("RANDOM()"))
    else:
        q = q.order_by(db.func.random())

    row = q.first()

    if not row and exclude_id:
        q2 = (
            PseudocodeQuestionBank.query
            .filter(col.isnot(None))
            .filter(db.func.length(col) > 0)
        )
        if "sqlite" in dialect:
            q2 = q2.order_by(db.text("RANDOM()"))
        else:
            q2 = q2.order_by(db.func.random())
        row = q2.first()

    if not row:
        resp = jsonify({"success": False, "message": f"No questions available for {level}."})
        resp = _no_cache(resp)
        resp = _corsify(resp)
        return resp, 404

    resp = jsonify({
        "success": True,
        "level": level,
        "question": getattr(row, level),
        "question_id": row.id
    })
    resp = _no_cache(resp)
    resp = _corsify(resp)
    return resp, 200


@pseudocode_bank_api.route("/ai_autofill", methods=["GET", "POST"])
def ai_autofill():
    if not _deepseek_ready():
        resp = jsonify({"success": False, "message": "DeepSeek API key not configured on server."})
        resp = _corsify(resp)
        return resp, 500

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        qid = data.get("question_id", None)
        level = data.get("level", None)
    else:
        qid = request.args.get("question_id", None)
        level = request.args.get("level", None)

    if qid is None:
        resp = jsonify({"success": False, "message": "Missing question_id"})
        resp = _corsify(resp)
        return resp, 400

    try:
        qid_int = int(qid)
    except Exception:
        resp = jsonify({"success": False, "message": "question_id must be an integer"})
        resp = _corsify(resp)
        return resp, 400

    row = PseudocodeQuestionBank.query.get(qid_int)
    if not row:
        resp = jsonify({"success": False, "message": "Question not found"})
        resp = _corsify(resp)
        return resp, 404

    question_text = None
    if level and hasattr(row, level):
        question_text = getattr(row, level)
    else:
        for colname in ["level1", "level2", "level3", "level4", "level5"]:
            val = getattr(row, colname, None)
            if val:
                question_text = val
                level = colname
                break

    if not question_text:
        resp = jsonify({"success": False, "message": "Question text not found"})
        resp = _corsify(resp)
        return resp, 404

    try:
        answer = ai_autofill_pseudocode(question_text)
        resp = jsonify({
            "success": True,
            "answer": answer,
            "question_id": qid_int,
            "level": level
        })
        resp = _corsify(resp)
        return resp, 200
    except Exception as e:
        resp = jsonify({"success": False, "message": str(e)})
        resp = _corsify(resp)
        return resp, 500


@pseudocode_bank_api.route("/grade", methods=["POST"])
def grade_question():
    data = request.get_json(silent=True) or {}

    qid = data.get("question_id", None)
    user_code = data.get("pseudocode", "")
    level = data.get("level", None)
    use_ai = bool(data.get("use_ai", True))

    if qid is None:
        resp = jsonify({"success": False, "message": "Missing question_id"})
        resp = _corsify(resp)
        return resp, 400

    row = PseudocodeQuestionBank.query.get(qid)
    if not row:
        resp = jsonify({"success": False, "message": "Question not found"})
        resp = _corsify(resp)
        return resp, 404

    question_text = None
    if level and hasattr(row, level):
        question_text = getattr(row, level)
    else:
        for colname in ["level1", "level2", "level3", "level4", "level5"]:
            val = getattr(row, colname, None)
            if val:
                question_text = val
                level = colname
                break

    if not question_text:
        resp = jsonify({"success": False, "message": "Question text not found"})
        resp = _corsify(resp)
        return resp, 404

    if use_ai and _deepseek_ready():
        try:
            ai = ai_grade_pseudocode(question_text, user_code)
            resp = jsonify({
                "success": True,
                "question_id": qid,
                "level": level,
                "passed": ai["passed"],
                "missing": ai["missing"],
                "notes": "AI grading enabled.",
                "feedback": ai["feedback"],
                "improved_pseudocode": ai["improved_pseudocode"]
            })
            resp = _corsify(resp)
            return resp, 200
        except Exception as e:
            print("AI grading failed, falling back:", e)

    result = grade_pseudocode(question_text, user_code)

    resp = jsonify({
        "success": True,
        "question_id": qid,
        "level": level,
        "passed": result["passed"],
        "missing": result["missing"],
        "notes": result["notes"],
        "feedback": "Rule-based checker used. Add the missing constructs and try again.",
        "improved_pseudocode": ""
    })
    resp = _corsify(resp)
    return resp, 200