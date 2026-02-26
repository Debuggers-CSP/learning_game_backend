# api/pseudocode_bank_api.py
from flask import Blueprint, request, jsonify, make_response
from __init__ import db
from model.pseudocode_bank import PseudocodeQuestionBank
from model.pseudocodeanswer1_bank import PseudocodeAnswerBank

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

_allowed = os.getenv("ALLOWED_ORIGINS", "").strip()
ALLOWED_ORIGINS = [o.strip() for o in _allowed.split(",") if o.strip()] or ["*"]


def _corsify(resp):
    origin = request.headers.get("Origin", "")

    if "*" in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    else:
        if origin in ALLOWED_ORIGINS:
            resp.headers["Access-Control-Allow-Origin"] = origin

    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Credentials"] = "false"
    return resp


def _no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@pseudocode_bank_api.route("/random", methods=["OPTIONS"])
@pseudocode_bank_api.route("/autofill", methods=["OPTIONS"])
@pseudocode_bank_api.route("/ai_autofill", methods=["OPTIONS"])
@pseudocode_bank_api.route("/grade", methods=["OPTIONS"])
def pseudocode_preflight():
    resp = make_response("", 204)
    resp = _no_cache(resp)
    resp = _corsify(resp)
    return resp


def _deepseek_ready() -> bool:
    return bool(DEEPSEEK_API_KEY)


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
        "You are a helpful AP CSP pseudocode grader.\n"
        "Return ONLY valid JSON (no markdown, no extra text).\n"
        "Be forgiving about formatting. Focus on logic and required steps.\n"
        "If it fails, list what is missing and give short actionable fixes.\n"
        "Always provide improved_pseudocode.\n"
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
- score_hint: integer 0..100 (estimate)
"""

    raw = _deepseek_chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.2,
        max_tokens=650
    )

    obj = _extract_json_object(raw)

    return {
        "passed": bool(obj.get("passed", False)),
        "missing": obj.get("missing", []) if isinstance(obj.get("missing", []), list) else [],
        "feedback": str(obj.get("feedback", "")).strip(),
        "improved_pseudocode": str(obj.get("improved_pseudocode", "")).strip(),
        "score_hint": int(obj.get("score_hint", 0)) if str(obj.get("score_hint", "")).isdigit() else 0
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


def grade_pseudocode_lenient(question_text: str, user_code: str):
    """
    Lenient keyword/structure checker.
    It helps students by telling them what's missing without being strict on syntax.
    """
    q = question_text or ""
    code = user_code or ""
    norm = _normalize(code)

    reqs = _requires(q)
    missing = []

    def has_any(tokens):
        return any(t in norm for t in tokens)

    if "input" in reqs and not has_any(["input", "read", "get ", "scan", "ask "]):
        missing.append("An INPUT step (example: INPUT x)")

    if "output" in reqs and not has_any(["display", "print", "output", "show "]):
        missing.append("A DISPLAY/OUTPUT step")

    if "if" in reqs and not has_any(["if", "else", "otherwise", "case", "switch"]):
        missing.append("An IF / ELSE decision")

    if "loop" in reqs and not has_any(["for", "while", "repeat", "loop", "each"]):
        missing.append("A LOOP (FOR, FOR EACH, WHILE, REPEAT)")

    if "function" in reqs and not has_any(["function", "procedure", "define"]):
        missing.append("A PROCEDURE/FUNCTION wrapper (if the prompt asks for one)")

    if "return" in reqs and "return" not in norm:
        missing.append("A RETURN statement")

    if "list" in reqs and not has_any(["list", "[", "]", "append", "add", "remove"]):
        missing.append("Some LIST use (create/access/append/remove)")

    if "even_odd_words" in reqs and not (("even" in norm) and ("odd" in norm)):
        missing.append('Both words "EVEN" and "ODD"')

    if "hot_word" in reqs and "hot" not in norm:
        missing.append('The word "Hot"')

    if "apcsp_word" in reqs and "apcsp" not in norm:
        missing.append('The literal "APCSP"')

    # Simple score hint
    total = max(1, len(reqs))
    hit = total - min(total, len(missing))
    score_hint = int((hit / total) * 100)

    return {
        "passed": len(missing) == 0,
        "missing": missing,
        "notes": "Lenient checker (focuses on required pieces, not strict syntax).",
        "score_hint": score_hint
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


@pseudocode_bank_api.route("/autofill", methods=["GET"])
def autofill_from_answer_bank():
    """
    ✅ Deterministic autofill: pulls canonical answer from PseudocodeAnswerBank.
    Query: /autofill?question_id=12
    """
    qid = request.args.get("question_id", type=int)
    if not qid:
        resp = jsonify({"success": False, "message": "Missing question_id"})
        resp = _corsify(resp)
        return resp, 400

    row = PseudocodeAnswerBank.query.filter_by(question_id=qid).first()
    if not row:
        resp = jsonify({"success": False, "message": "Answer not found in answer bank"})
        resp = _corsify(resp)
        return resp, 404

    resp = jsonify({
        "success": True,
        "source": "answer_bank",
        "question_id": qid,
        "level": row.level,
        "answer": row.answer
    })
    resp = _no_cache(resp)
    resp = _corsify(resp)
    return resp, 200


@pseudocode_bank_api.route("/ai_autofill", methods=["GET", "POST"])
def ai_autofill():
    """
    AI autofill fallback if answer bank not used.
    """
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
            "source": "ai",
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

    # Prefer AI grading if available
    if use_ai and _deepseek_ready():
        try:
            ai = ai_grade_pseudocode(question_text, user_code)
            resp = jsonify({
                "success": True,
                "question_id": qid,
                "level": level,
                "passed": ai["passed"],
                "missing": ai["missing"],
                "notes": "AI grading enabled (forgiving about formatting).",
                "feedback": ai["feedback"],
                "improved_pseudocode": ai["improved_pseudocode"],
                "score_hint": ai["score_hint"]
            })
            resp = _corsify(resp)
            return resp, 200
        except Exception as e:
            print("AI grading failed, falling back:", e)

    # Fallback: lenient rule-based grading
    result = grade_pseudocode_lenient(question_text, user_code)

    resp = jsonify({
        "success": True,
        "question_id": qid,
        "level": level,
        "passed": result["passed"],
        "missing": result["missing"],
        "notes": result["notes"],
        "feedback": "Add the missing pieces and try again. You are close.",
        "improved_pseudocode": "",
        "score_hint": result["score_hint"]
    })
    resp = _corsify(resp)
    return resp, 200