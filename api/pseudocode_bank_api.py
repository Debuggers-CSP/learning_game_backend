# api/pseudocode_bank_api.py

from __init__ import app, db
from flask import Blueprint, jsonify, request
import random
import re
from difflib import SequenceMatcher

from model.pseudocode_bank import PseudocodeQuestionBank
from model.pseudocodeanswer_bank import PseudocodeAnswerBank

pseudocode_bank_api = Blueprint("pseudocode_bank_api", __name__, url_prefix="/api/pseudocode_bank")


# -----------------------------
# Helpers
# -----------------------------
def _level_to_col(level_num: int) -> str:
    return {
        1: "level1",
        2: "level2",
        3: "level3",
        4: "level4",
        5: "level5",
    }.get(level_num, "level1")


def _strip_comments(line: str) -> str:
    # remove common comment styles
    if line is None:
        return ""
    s = str(line)
    s = re.sub(r"//.*$", "", s)
    s = re.sub(r"#.*$", "", s)
    return s


def _canon_text(s: str) -> str:
    """
    Canonicalize pseudocode for fair matching:
    - normalize arrows and operators
    - lowercase
    - remove extra whitespace
    - remove punctuation that shouldn't matter (; , parentheses)
    """
    if s is None:
        return ""
    s = str(s)

    # normalize symbols
    s = s.replace("←", "<-")
    s = s.replace("→", "->")
    s = s.replace("≥", ">=")
    s = s.replace("≤", "<=")
    s = s.replace("≠", "!=")

    s = s.lower()

    # remove punctuation that frequently differs
    s = re.sub(r"[;,]", " ", s)
    s = re.sub(r"[()\[\]{}]", " ", s)

    # normalize assignment arrows ( <- ) to =
    s = re.sub(r"\s*<-\s*", " = ", s)

    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _canon_lines(s: str) -> list[str]:
    """
    Split into meaningful lines.
    """
    if s is None:
        return []
    raw_lines = str(s).replace("\r\n", "\n").split("\n")
    out = []
    for ln in raw_lines:
        ln = _strip_comments(ln)
        ln = _canon_text(ln)
        if ln:
            out.append(ln)
    return out


def _subsequence_match(needle_lines: list[str], hay_lines: list[str]) -> tuple[bool, list[str]]:
    """
    Check if all needle_lines appear in hay_lines in order (not necessarily consecutive).
    Returns (passed, missing_lines)
    """
    if not needle_lines:
        return False, ["<empty answer key>"]
    if not hay_lines:
        return False, needle_lines

    i = 0
    missing = []
    for n in needle_lines:
        found = False
        while i < len(hay_lines):
            if n == hay_lines[i] or n in hay_lines[i]:
                found = True
                i += 1
                break
            i += 1
        if not found:
            missing.append(n)

    return (len(missing) == 0), missing


def _similarity_score(a: str, b: str) -> float:
    """
    Similarity on canonicalized whole text.
    """
    return SequenceMatcher(None, a, b).ratio()


def _get_question_text(row: PseudocodeQuestionBank, col: str) -> str:
    return getattr(row, col, None)


# -----------------------------
# Routes
# -----------------------------
@pseudocode_bank_api.get("/random")
def get_random_question():
    """
    GET /api/pseudocode_bank/random?level=1&exclude_id=3

    Response:
      { success, level, question_id, question }
    """
    level_num = request.args.get("level", default=1, type=int)
    exclude_id = request.args.get("exclude_id", default=None, type=int)

    col = _level_to_col(level_num)

    q = PseudocodeQuestionBank.query
    if exclude_id:
        q = q.filter(PseudocodeQuestionBank.id != exclude_id)

    rows = q.all()
    candidates = [r for r in rows if (_get_question_text(r, col) or "").strip()]

    if not candidates:
        return jsonify({
            "success": False,
            "message": f"No questions available for level {level_num} ({col})."
        }), 404

    row = random.choice(candidates)
    return jsonify({
        "success": True,
        "level": col,
        "question_id": row.id,
        "question": _get_question_text(row, col)
    }), 200


@pseudocode_bank_api.get("/autofill")
def autofill_from_answer_bank():
    """
    GET /api/pseudocode_bank/autofill?question_id=1&level=level1

    Response:
      { success, question_id, level, answer }
    """
    question_id = request.args.get("question_id", type=int)
    level = request.args.get("level", default=None, type=str)

    if not question_id:
        return jsonify({"success": False, "message": "Missing required query param: question_id"}), 400

    ans = PseudocodeAnswerBank.query.filter_by(question_id=question_id).first()
    if not ans:
        return jsonify({"success": False, "message": f"No answer found for question_id={question_id}"}), 404

    if level and ans.level and str(level).strip() != str(ans.level).strip():
        return jsonify({
            "success": True,
            "question_id": question_id,
            "level": ans.level,
            "answer": ans.answer,
            "warning": f"Requested level={level}, but DB level={ans.level}"
        }), 200

    return jsonify({
        "success": True,
        "question_id": question_id,
        "level": ans.level,
        "answer": ans.answer
    }), 200


@pseudocode_bank_api.post("/ai_autofill")
def ai_autofill_compat():
    """
    Compatibility endpoint.
    Returns DB answer (not AI).
    """
    body = request.get_json(silent=True) or {}
    question_id = body.get("question_id")

    if not question_id:
        return jsonify({"success": False, "message": "question_id is required"}), 400

    ans = PseudocodeAnswerBank.query.filter_by(question_id=int(question_id)).first()
    if not ans:
        return jsonify({"success": False, "message": f"No answer found for question_id={question_id}"}), 404

    return jsonify({"success": True, "answer": ans.answer, "level": ans.level}), 200


@pseudocode_bank_api.post("/grade")
def grade_pseudocode():
    """
    ✅ Answer-key based grading (NOT rubric/AI).
    Passes if:
      - canonical similarity is high, OR
      - answer-key lines appear in order (subsequence match)

    This prevents the “it demands a loop” nonsense when your answer is correct.
    """
    body = request.get_json(silent=True) or {}

    question_id = body.get("question_id")
    level = body.get("level")
    user_code = body.get("pseudocode", "")

    if not question_id:
        return jsonify({"success": False, "message": "question_id is required"}), 400

    ans = PseudocodeAnswerBank.query.filter_by(question_id=int(question_id)).first()
    if not ans:
        return jsonify({"success": False, "message": f"No answer found for question_id={question_id}"}), 404

    key_text = ans.answer or ""
    user_text = user_code or ""

    # Canonical whole-text similarity
    user_whole = " ".join(_canon_lines(user_text))
    key_whole = " ".join(_canon_lines(key_text))
    sim = _similarity_score(user_whole, key_whole)

    # Canonical line-based subsequence
    key_lines = _canon_lines(key_text)
    user_lines = _canon_lines(user_text)
    subseq_pass, missing_lines = _subsequence_match(key_lines, user_lines)

    # Threshold: if user pasted the exact correct answer, this always passes
    passed = (sim >= 0.92) or subseq_pass

    if passed:
        return jsonify({
            "success": True,
            "passed": True,
            "question_id": int(question_id),
            "level": ans.level or level,
            "feedback": f"✅ Correct. Matched the answer key (similarity={sim:.2f}).",
            "missing": [],
            "improved_pseudocode": key_text
        }), 200

    # Helpful debug: show what key lines were missing (canonical form)
    return jsonify({
        "success": True,
        "passed": False,
        "question_id": int(question_id),
        "level": ans.level or level,
        "feedback": f"⚠️ Not quite. Compare to the example passing solution (similarity={sim:.2f}).",
        "missing": missing_lines[:12],  # cap so it doesn't spam
        "improved_pseudocode": key_text
    }), 200


# -----------------------------
# Registration (so paste works)
# -----------------------------
def register_pseudocode_bank_api(flask_app):
    if "pseudocode_bank_api" not in flask_app.blueprints:
        flask_app.register_blueprint(pseudocode_bank_api)


register_pseudocode_bank_api(app)