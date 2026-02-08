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

import re

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
            # allow a pass if they clearly do string operations without those keywords
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


@pseudocode_bank_api.route("/random", methods=["GET"])
def random_question():
    level = _resolve_level(request.args.get("level", "1"))
    if level not in VALID_COLS:
        return jsonify({
            "success": False,
            "message": "Invalid level. Use 1-5 or super_easy/easy/medium/hard/hacker."
        }), 400

    col = getattr(PseudocodeQuestionBank, level)

    row = (
        PseudocodeQuestionBank.query
        .filter(col.isnot(None))
        .filter(col != "")
        .order_by(db.func.random())
        .first()
    )

    if not row:
        return jsonify({"success": False, "message": f"No questions available for {level}."}), 404

    return jsonify({
        "success": True,
        "level": level,
        "question": getattr(row, level),
        "question_id": row.id
    }), 200


@pseudocode_bank_api.route("/grade", methods=["POST"])
def grade_question():
    data = request.get_json(silent=True) or {}

    qid = data.get("question_id", None)
    user_code = data.get("pseudocode", "")
    level = data.get("level", None)

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

    result = grade_pseudocode(question_text, user_code)

    return jsonify({
        "success": True,
        "question_id": qid,
        "level": level,
        "passed": result["passed"],
        "missing": result["missing"],
        "notes": result["notes"]
    }), 200
