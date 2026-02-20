# api/pseudocode_bank_api.py

from flask import Blueprint, request, jsonify
from __init__ import db
from model.pseudocode_bank import PseudocodeQuestionBank

pseudocode_bank_api = Blueprint("pseudocode_bank_api", __name__, url_prefix="/api/pseudocode_bank")

LEVEL_MAP = {
    # numeric
    "1": "level1",
    "2": "level2",
    "3": "level3",
    "4": "level4",
    "5": "level5",

    # named
    "super_easy": "level1",
    "super easy": "level1",
    "easy": "level2",
    "medium": "level3",
    "hard": "level4",
    "hacker": "level5",
}

VALID_COLS = {"level1", "level2", "level3", "level4", "level5"}

import os
import requests
import re

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions").strip()

def _deepseek_ready() -> bool:
    return bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "YOUR_API_KEY_HERE")

def _deepseek_chat(messages, temperature=0.2, max_tokens=500):
    """
    Calls DeepSeek chat completions. Returns raw string content.
    """
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
    """
    DeepSeek sometimes wraps JSON with extra text. This extracts the first {...} block.
    """
    s = (text or "").strip()
    if s.startswith("```"):
        s = s.replace("```json", "").replace("```", "").strip()

    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in AI output")

    import json as _json
    return _json.loads(s[start:end+1])

def ai_grade_pseudocode(question_text: str, user_code: str) -> dict:
    """
    Returns:
      {
        "passed": bool,
        "missing": [str],
        "feedback": str,
        "improved_pseudocode": str
      }
    """
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

    # Defensive defaults if the model omits something
    return {
        "passed": bool(obj.get("passed", False)),
        "missing": obj.get("missing", []) if isinstance(obj.get("missing", []), list) else [],
        "feedback": str(obj.get("feedback", "")).strip(),
        "improved_pseudocode": str(obj.get("improved_pseudocode", "")).strip()
    }

def ai_autofill_pseudocode(question_text: str) -> str:
    """
    Generates a full pseudocode solution for the prompt.
    Returns plain text pseudocode.
    """
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

    # If it wrapped in ``` remove it
    out = raw.strip()
    if out.startswith("```"):
        out = out.replace("```", "").replace("json", "").strip()
    return out


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def _requires(prompt: str):
    """
    Returns a list of requirement keys based on the prompt text.
    Keep this small and reliable (keyword-style).
    """
    p = _normalize(prompt)

    req = []

    # common actions
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

    # conditionals / loops / functions
    if "if" in p or "otherwise" in p or "else" in p or "decision" in p:
        req.append("if")
    if "loop" in p or "for " in p or "from" in p or "times" in p or "1 to" in p or "1..":
        req.append("loop")
    if "write " in p or "returns" in p or "return" in p or "(" in p and ")" in p and "write" in p:
        req.append("function")
    if "return" in p or "returns" in p:
        req.append("return")

    # list/string specific hints
    if "list" in p:
        req.append("list")
    if "string" in p:
        req.append("string")

    # special literals in your question bank that are easy to check
    if '"even"' in p or " even " in p and '"odd"' in p or " odd " in p:
        req.append("even_odd_words")
    if '"hot"' in p:
        req.append("hot_word")
    if '"apcsp"' in p:
        req.append("apcsp_word")

    return req

def grade_pseudocode(question_text: str, user_code: str):
    """
    Very lightweight rule-based checker.
    It checks for required constructs, not perfect logic.
    """
    q = question_text or ""
    code = user_code or ""
    norm = _normalize(code)

    reqs = _requires(q)
    missing = []

    def has_any(tokens):
        return any(t in norm for t in tokens)

    # Input
    if "input" in reqs:
        if not has_any(["input", "read", "get ", "scan", "ask "]):
            missing.append("An INPUT step (e.g., INPUT x)")

    # Output
    if "output" in reqs:
        if not has_any(["display", "print", "output", "show "]):
            missing.append("Output the final result")

    # Actions list
    if "actions" in reqs:
        if not has_any(["action", "actions", "event", "step"]):
            missing.append("Process each action in order")

    # Result variable
    if "result" in reqs:
        if not has_any(["result", "score", "state", "status", "outcome", "count", "total"]):
            missing.append("Define and update a result")

    # If/Else
    if "if" in reqs:
        if not has_any(["if", "else", "otherwise", "case", "switch"]):
            missing.append("Use if/else decisions for actions")

    # Loop
    if "loop" in reqs:
        if not has_any(["for", "while", "repeat", "loop", "each"]):
            missing.append("Loop once per action")

    # Unknown action handling
    if "unknown" in reqs:
        if not has_any(["unknown", "default", "otherwise", "else"]):
            missing.append("Handle unknown actions safely")

    # Function
    if "function" in reqs:
        if not has_any(["function", "procedure", "define", "def "]):
            missing.append("A FUNCTION/PROCEDURE definition")

    # Return
    if "return" in reqs:
        if "return" not in norm:
            missing.append("A RETURN statement")

    # Lists
    if "list" in reqs:
        if not has_any(["list", "[", "]", "append", "add", "remove"]):
            missing.append("Some LIST handling (list creation/access/append/remove)")

    # Strings
    if "string" in reqs:
        if not has_any(["string", "char", "substring", "length", "letters"]):
            if not re.search(r"[a-zA-Z]", code):
                missing.append("Some STRING handling")

    # Special literal checks
    if "even_odd_words" in reqs:
        if not (("even" in norm) and ("odd" in norm)):
            missing.append('Both output words "EVEN" and "ODD"')

    if "hot_word" in reqs:
        if "hot" not in norm:
            missing.append('Output word "Hot"')

    if "apcsp_word" in reqs:
        if "apcsp" not in norm:
            missing.append('Use the literal "APCSP" in the comparison/output')

    passed = (len(missing) == 0)

    return {
        "passed": passed,
        "missing": missing,
        "notes": "This checker validates required structures/keywords for the prompt."
    }


def _resolve_level(raw: str) -> str:
    raw = (raw or "").strip().lower()
    return LEVEL_MAP.get(raw, raw)


# ============================================================
# ✅ RANDOM ENDPOINT FIX: prevent caching + reliable randomness
# ============================================================
@pseudocode_bank_api.route("/random", methods=["GET"])
def random_question():
    level = _resolve_level(request.args.get("level", "1"))
    if level not in VALID_COLS:
        resp = jsonify({
            "success": False,
            "message": "Invalid level. Use 1-5 or super_easy/easy/medium/hard/hacker."
        })
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp, 400

    col = getattr(PseudocodeQuestionBank, level)

    # Better empty filtering than col != ""
    q = (
        PseudocodeQuestionBank.query
        .filter(col.isnot(None))
        .filter(db.func.length(col) > 0)
    )

    # Dialect-safe random ordering
    dialect = (db.session.bind.dialect.name or "").lower() if db.session.bind else ""
    if "sqlite" in dialect:
        q = q.order_by(db.text("RANDOM()"))
    else:
        q = q.order_by(db.func.random())

    row = q.first()

    if not row:
        resp = jsonify({"success": False, "message": f"No questions available for {level}."})
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp, 404

    resp = jsonify({
        "success": True,
        "level": level,
        "question": getattr(row, level),
        "question_id": row.id
    })

    # Critical: never cache a random response
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp, 200


@pseudocode_bank_api.route("/ai_autofill", methods=["GET"])
def ai_autofill():
    """
    GET /api/pseudocode_bank/ai_autofill?question_id=123&level=level3
    Returns: { success, answer }
    """
    if not _deepseek_ready():
        return jsonify({
            "success": False,
            "message": "DeepSeek API key not configured on server."
        }), 500

    qid = request.args.get("question_id", None)
    level = request.args.get("level", None)

    if qid is None:
        return jsonify({"success": False, "message": "Missing question_id"}), 400

    try:
        qid_int = int(qid)
    except Exception:
        return jsonify({"success": False, "message": "question_id must be an integer"}), 400

    row = PseudocodeQuestionBank.query.get(qid_int)
    if not row:
        return jsonify({"success": False, "message": "Question not found"}), 404

    question_text = None
    if level and hasattr(row, level):
        question_text = getattr(row, level)
    else:
        for col in ["level1", "level2", "level3", "level4", "level5"]:
            val = getattr(row, col, None)
            if val:
                question_text = val
                level = col
                break

    if not question_text:
        return jsonify({"success": False, "message": "Question text not found"}), 404

    try:
        answer = ai_autofill_pseudocode(question_text)
        return jsonify({
            "success": True,
            "answer": answer,
            "question_id": qid_int,
            "level": level
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@pseudocode_bank_api.route("/grade", methods=["POST"])
def grade_question():
    data = request.get_json(silent=True) or {}

    qid = data.get("question_id", None)
    user_code = data.get("pseudocode", "")
    level = data.get("level", None)

    # NEW: front end can request AI grading
    use_ai = bool(data.get("use_ai", True))

    if qid is None:
        return jsonify({"success": False, "message": "Missing question_id"}), 400

    row = PseudocodeQuestionBank.query.get(qid)
    if not row:
        return jsonify({"success": False, "message": "Question not found"}), 404

    question_text = None
    if level and hasattr(row, level):
        question_text = getattr(row, level)
    else:
        for col in ["level1", "level2", "level3", "level4", "level5"]:
            val = getattr(row, col, None)
            if val:
                question_text = val
                level = col
                break

    if not question_text:
        return jsonify({"success": False, "message": "Question text not found"}), 404

    # ----- AI grading path -----
    if use_ai and _deepseek_ready():
        try:
            ai = ai_grade_pseudocode(question_text, user_code)
            return jsonify({
                "success": True,
                "question_id": qid,
                "level": level,
                "passed": ai["passed"],
                "missing": ai["missing"],
                "notes": "AI grading enabled.",
                "feedback": ai["feedback"],
                "improved_pseudocode": ai["improved_pseudocode"]
            }), 200
        except Exception as e:
            print("AI grading failed, falling back:", e)

    # ----- Rule-based fallback -----
    result = grade_pseudocode(question_text, user_code)

    return jsonify({
        "success": True,
        "question_id": qid,
        "level": level,
        "passed": result["passed"],
        "missing": result["missing"],
        "notes": result["notes"],
        "feedback": "Rule-based checker used. Add the missing constructs and try again.",
        "improved_pseudocode": ""
    }), 200