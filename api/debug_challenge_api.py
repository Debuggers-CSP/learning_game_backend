from datetime import datetime
import ast
import json
import re
import subprocess
import tempfile
import os

from flask import Blueprint, request, jsonify

from __init__ import db
from model.debug_challenge import DebugChallenge, DebugBadge, DebugBadgeEarned, DebugHintUsage
from model.endgame import Player


debug_challenge_api = Blueprint("debug_challenge_api", __name__, url_prefix="/api/debug_challenge")

LEVEL_MAP = {
    "1": "beginner",
    "2": "intermediate",
    "3": "hard",
    "beginner": "beginner",
    "intermediate": "intermediate",
    "hard": "hard",
}

LEVEL_DETAILS = {
    "beginner": {
        "label": "Beginner",
        "focus": "Basic syntax and simple logic",
    },
    "intermediate": {
        "label": "Intermediate",
        "focus": "Loops, lists, and conditionals",
    },
    "hard": {
        "label": "Hard",
        "focus": "Multiple concepts and real-world style problems",
    },
}

CHAT_ROLES = {
    "hint_coach": "Hint Coach",
    "debugger": "Debugger",
    "teacher": "Teacher",
    "checker": "Checker",
}


def _resolve_level(raw: str) -> str:
    key = (raw or "").strip().lower()
    return LEVEL_MAP.get(key, "")


def _normalize(text: str) -> str:
    if not text:
        return ""
    cleaned = text.lower()
    cleaned = re.sub(r"[^a-z0-9_]+", " ", cleaned)
    return " ".join(cleaned.split())


def _parse_keywords(raw: str) -> list:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        return []
    return []


def _role_response(role: str, challenge: DebugChallenge, student_text: str) -> str:
    prompt = (challenge.prompt or "").strip()
    expected = (challenge.expected_behavior or "").strip()
    code = (challenge.buggy_code or "").strip()
    role_key = role.lower()

    if role_key == "hint_coach":
        return (
            "Focus on one small change at a time. "
            "Check the condition, operator, or indentation first. "
            "Look for a single line that would prevent the expected behavior."
        )
    if role_key == "debugger":
        return (
            "Scan the line that controls the decision or loop. "
            "If the behavior is wrong, the bug is likely in the condition or the update line."
        )
    if role_key == "teacher":
        return (
            f"Concept: {prompt} "
            "Read the code top to bottom, and track how values change each line. "
            "The fix should make the behavior match the description."
        )
    if role_key == "checker":
        if not student_text.strip():
            return "Share your fix or explanation, and I’ll check it against the expected behavior."
        result = _grade_answer(challenge, student_text)
        if result["passed"]:
            return "Looks aligned with the expected behavior. Re-run the case to confirm."
        hint = result["hints"][0] if result["hints"] else "Re-check the condition and output."
        return f"Not quite yet. {hint}"
    return "Choose a role: Hint Coach, Debugger, Teacher, or Checker."


def _keyword_hints(missing: list) -> list:
    hints = []
    if any(word in missing for word in ["if", "else"]):
        hints.append("Check the decision logic (if/else) for the condition.")
    if "for" in missing or "while" in missing or "range" in missing:
        hints.append("Review the loop structure and make sure it runs correctly.")
    if "print" in missing:
        hints.append("Make sure the output line prints the correct value.")
    if "append" in missing:
        hints.append("Check how items are added to the list.")
    if "return" in missing:
        hints.append("Make sure the function returns the correct result.")
    if "break" in missing:
        hints.append("Consider whether the loop should stop when a condition is met.")
    if not hints:
        hints.append("Re-check variable names, operators, and indentation.")
    return hints[:3]


def _strip_code_fences(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).strip("`") or "", text)
    return cleaned.strip()


def _looks_like_code(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    code_tokens = [
        "def ",
        "return ",
        "print(",
        "for ",
        "while ",
        "if ",
        "elif ",
        "else:",
        "class ",
    ]
    return ("\n" in text and any(token in lowered for token in code_tokens))


def _check_python_syntax(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return True, "OK"
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc.msg} (line {exc.lineno})"


def _normalize_output(text: str) -> str:
    if text is None:
        return ""
    lines = [line.strip() for line in str(text).splitlines()]
    return "\n".join(line for line in lines if line != "")


def _matches_expected(actual: str, expected: str) -> bool:
    if expected is None:
        return True
    actual_norm = _normalize_output(actual)
    actual_compact = re.sub(r"\s+", "", actual_norm)
    expected_options = [opt.strip() for opt in expected.split("|") if opt.strip()]
    for option in expected_options:
        expected_norm = _normalize_output(option)
        expected_compact = re.sub(r"\s+", "", expected_norm)
        if actual_norm == expected_norm or actual_compact == expected_compact:
            return True
    return False


def _run_code(code: str) -> tuple[bool, str]:
    if not code.strip():
        return False, "No code provided."
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
            output = (result.stdout or "") + (result.stderr or "")
            return True, output
        except subprocess.TimeoutExpired:
            return False, "⏱️ Execution timed out (5 s limit)."
        except Exception as exc:
            return False, f"Error running code: {str(exc)}"
        finally:
            os.unlink(tmp.name)


def _grade_answer(challenge: DebugChallenge, answer: str) -> dict:
    if not answer or not answer.strip():
        return {
            "passed": False,
            "missing": ["Provide a fix or explanation"],
            "hints": ["Explain what is wrong and how you would correct it."],
            "notes": "This checker looks for key ideas, not perfect syntax."
        }

    cleaned_answer = _strip_code_fences(answer)
    if not _looks_like_code(cleaned_answer):
        return {
            "passed": False,
            "missing": ["Submit Python code only"],
            "hints": ["Paste corrected Python code (not a sentence)."],
            "notes": "This challenge only accepts code submissions."
        }

    ok, message = _check_python_syntax(cleaned_answer)
    if not ok:
        return {
            "passed": False,
            "missing": ["Fix syntax errors before submitting"],
            "hints": [message],
            "notes": "Syntax must be valid before grading."
        }

    test_harness = (challenge.test_harness or "").strip()
    to_run = f"{cleaned_answer}\n{test_harness}" if test_harness else cleaned_answer
    ok, output = _run_code(to_run)
    if not ok:
        return {
            "passed": False,
            "missing": ["Code did not run"],
            "hints": [output],
            "notes": "Fix runtime errors and try again."
        }

    if challenge.expected_output is not None:
        if not _matches_expected(output, challenge.expected_output):
            return {
                "passed": False,
                "missing": ["Output does not match expected result"],
                "hints": ["Check loop bounds, conditions, and print output."],
                "notes": "Your code runs but produces the wrong output."
            }

    required = _parse_keywords(challenge.solution_keywords)
    if not required:
        return {
            "passed": True,
            "missing": [],
            "hints": [],
            "notes": "Answer received."
        }

    normalized = _normalize(answer)
    missing = []
    for keyword in required:
        if keyword.startswith("re:"):
            pattern = keyword.replace("re:", "", 1)
            if not re.search(pattern, answer, re.IGNORECASE):
                missing.append(keyword)
        else:
            if keyword not in normalized:
                missing.append(keyword)

    passed = len(missing) == 0
    return {
        "passed": passed,
        "missing": missing,
        "hints": [] if passed else _keyword_hints(missing),
        "notes": "This checker looks for key ideas, not perfect syntax."
    }


def _get_or_create_player(player_id: int) -> Player:
    player = Player.query.get(player_id)
    if player:
        return player
    player = Player(id=player_id, username=f"Player {player_id}")
    db.session.add(player)
    db.session.commit()
    return player


def _get_or_create_hint_usage(player_id: int, level: str, challenge_id: int) -> DebugHintUsage:
    usage = DebugHintUsage.query.filter_by(
        player_id=player_id,
        level=level,
        challenge_id=challenge_id,
    ).first()
    if usage:
        return usage
    usage = DebugHintUsage(
        player_id=player_id,
        level=level,
        challenge_id=challenge_id,
        hints_used=0,
        updated_at=datetime.utcnow(),
    )
    db.session.add(usage)
    db.session.commit()
    return usage


@debug_challenge_api.route("/levels", methods=["GET"])
def get_levels():
    levels = []
    for key, info in LEVEL_DETAILS.items():
        badge = DebugBadge.query.filter_by(level=key).first()
        levels.append({
            "level": key,
            "label": info["label"],
            "focus": info["focus"],
            "badge": badge.badge_name if badge else None
        })
    return jsonify({"success": True, "levels": levels}), 200


@debug_challenge_api.route("/roles", methods=["GET"])
def get_roles():
    return jsonify({
        "success": True,
        "roles": [
            {"key": key, "label": label}
            for key, label in CHAT_ROLES.items()
        ]
    }), 200


@debug_challenge_api.route("/random", methods=["GET"])
def random_challenge():
    level = _resolve_level(request.args.get("level", ""))
    if not level:
        return jsonify({
            "success": False,
            "message": "Invalid level. Use beginner/intermediate/hard."
        }), 400

    row = (
        DebugChallenge.query
        .filter_by(level=level)
        .order_by(db.func.random())
        .first()
    )

    if not row:
        return jsonify({"success": False, "message": f"No challenges for {level}."}), 404

    return jsonify({
        "success": True,
        "challenge": row.to_dict()
    }), 200


@debug_challenge_api.route("/start", methods=["POST"])
def start_challenge():
    data = request.get_json(silent=True) or {}
    level = _resolve_level(data.get("level", ""))
    if not level:
        return jsonify({
            "success": False,
            "message": "Choose a level before starting: beginner/intermediate/hard."
        }), 400

    row = (
        DebugChallenge.query
        .filter_by(level=level)
        .order_by(db.func.random())
        .first()
    )
    if not row:
        return jsonify({"success": False, "message": f"No challenges for {level}."}), 404

    badge = DebugBadge.query.filter_by(level=level).first()
    return jsonify({
        "success": True,
        "level": level,
        "badge": badge.badge_name if badge else None,
        "challenge": row.to_dict()
    }), 200


@debug_challenge_api.route("/grade", methods=["POST"])
def grade_challenge():
    data = request.get_json(silent=True) or {}
    challenge_id = data.get("challenge_id")
    answer = data.get("answer", "")

    if not challenge_id:
        return jsonify({"success": False, "message": "Missing challenge_id."}), 400

    row = DebugChallenge.query.get(challenge_id)
    if not row:
        return jsonify({"success": False, "message": "Challenge not found."}), 404

    result = _grade_answer(row, answer)

    return jsonify({
        "success": True,
        "challenge_id": row.id,
        "level": row.level,
        "passed": result["passed"],
        "missing": result["missing"],
        "hints": result["hints"],
        "notes": result["notes"],
    }), 200


@debug_challenge_api.route("/chat", methods=["POST"])
def chat_with_role():
    data = request.get_json(silent=True) or {}
    challenge_id = data.get("challenge_id")
    role = (data.get("role") or "").strip().lower()
    message = data.get("message", "")
    player_id = data.get("player_id")

    if not challenge_id:
        return jsonify({"success": False, "message": "Missing challenge_id."}), 400
    if role not in CHAT_ROLES:
        return jsonify({"success": False, "message": "Invalid role."}), 400

    row = DebugChallenge.query.get(challenge_id)
    if not row:
        return jsonify({"success": False, "message": "Challenge not found."}), 404

    remaining_hints = None
    if role == "hint_coach" and player_id is not None:
        player_id = int(player_id)
        _get_or_create_player(player_id)
        usage = _get_or_create_hint_usage(player_id, row.level, row.id)
        if usage.hints_used < 3:
            usage.hints_used += 1
            usage.updated_at = datetime.utcnow()
            db.session.commit()
        remaining_hints = max(0, 3 - usage.hints_used)
        if usage.hints_used >= 3:
            reply = (
                "Hint limit reached. You can still try on your own, "
                "but using all 3 hints means no badge for this level."
            )
        else:
            reply = _role_response(role, row, message)
    else:
        reply = _role_response(role, row, message)

    response = {
        "success": True,
        "role": role,
        "reply": reply,
    }
    if remaining_hints is not None:
        response["remaining_hints"] = remaining_hints
    return jsonify(response), 200


@debug_challenge_api.route("/complete", methods=["POST"])
def complete_level():
    data = request.get_json(silent=True) or {}
    player_id = data.get("player_id")
    level = _resolve_level(data.get("level", ""))
    attempts = data.get("attempts")
    passed = data.get("passed", False)

    if player_id is None or not level:
        return jsonify({"success": False, "message": "Missing player_id or level."}), 400

    if attempts is None or not isinstance(attempts, int) or attempts < 0:
        return jsonify({"success": False, "message": "Invalid attempts."}), 400

    if not passed:
        return jsonify({"success": True, "message": "Attempt recorded."}), 200

    player_id = int(player_id)
    _get_or_create_player(player_id)
    usage = DebugHintUsage.query.filter_by(
        player_id=player_id,
        level=level,
    ).order_by(DebugHintUsage.updated_at.desc()).first()
    if usage and usage.hints_used >= 3:
        return jsonify({
            "success": True,
            "message": "Correct, but badge not awarded because all 3 hints were used."
        }), 200
    badge = DebugBadge.query.filter_by(level=level).first()
    if not badge:
        return jsonify({"success": False, "message": "Badge not configured."}), 500

    existing = DebugBadgeEarned.query.filter_by(player_id=player_id, badge_id=badge.id).first()
    if existing:
        existing.attempts = attempts
        existing.timestamp = datetime.utcnow()
    else:
        db.session.add(DebugBadgeEarned(
            player_id=player_id,
            badge_id=badge.id,
            attempts=attempts,
        ))

    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"Badge '{badge.badge_name}' saved.",
        "badge": badge.to_dict()
    }), 201


@debug_challenge_api.route("/player/<int:player_id>/progress", methods=["GET"])
def player_progress(player_id: int):
    earned = (
        DebugBadgeEarned.query
        .filter_by(player_id=player_id)
        .order_by(DebugBadgeEarned.timestamp.asc())
        .all()
    )
    return jsonify({
        "success": True,
        "player_id": player_id,
        "badges": [row.to_dict() for row in earned]
    }), 200
