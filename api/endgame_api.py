from datetime import datetime
import json
import re

import requests
from flask import Blueprint, jsonify, request, current_app

from __init__ import db
from model.endgame import Player, Badge, PlayerBadge

endgame_api = Blueprint("endgame_api", __name__)


def _get_json():
    return request.get_json(silent=True) or {}


def _normalize_answer(answer: str) -> str:
    return " ".join(answer.strip().split())


def _parse_iso(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _strip_code_blocks(text: str) -> str:
    if not text:
        return ""
    # Remove fenced code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code backticks
    text = re.sub(r"`([^`]*)`", r"\1", text)
    # Remove leftover double spaces
    return " ".join(text.split())


def _call_gemini(prompt: str, text: str) -> str:
    api_key = current_app.config.get("GEMINI_API_KEY")
    server = current_app.config.get("GEMINI_SERVER")
    if not api_key or not server:
        return ""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{prompt}\n\n{text}"}
                ]
            }
        ]
    }

    try:
        response = requests.post(
            f"{server}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        if response.status_code != 200:
            return ""
        gemini_json = response.json()
        raw_text = gemini_json["candidates"][0]["content"]["parts"][0]["text"]
        return _strip_code_blocks(raw_text)
    except (requests.RequestException, KeyError, IndexError, TypeError):
        return ""


def _fallback_grade(answer: str) -> dict:
    expected = current_app.config.get("FINAL_CODE_ANSWER", "")
    normalized_answer = _normalize_answer(answer)
    normalized_expected = _normalize_answer(expected)
    correct = bool(normalized_expected) and normalized_answer == normalized_expected
    if correct:
        return {"correct": True, "message": "Correct", "steps": []}
    return {
        "correct": False,
        "message": "Unable to verify correctness. Please review and retry.",
        "steps": [
            "Re-check the problem requirements and expected output.",
            "Compare your solution structure with the expected approach.",
            "Fix any syntax or logic errors, then try again."
        ]
    }


def _grade_final_answer(answer: str) -> dict:
    result = None
    prompt = (
        "You are grading a student's final code answer. "
        "Return ONLY valid JSON with this schema: "
        "{\"verdict\":\"Correct\"|\"Incorrect\",\"explanation\":string,\"steps\":string[]}\n"
        "If verdict is Correct, explanation should be 'Correct' and steps must be an empty array. "
        "If verdict is Incorrect, provide a short explanation and 3-6 numbered fix steps as strings."
    )

    gemini_text = _call_gemini(prompt, f"Student answer:\n{answer}")
    if gemini_text:
        parsed = _extract_json(gemini_text)
        verdict = (parsed.get("verdict") or "").strip().lower()
        explanation = (parsed.get("explanation") or "").strip()
        steps = parsed.get("steps") if isinstance(parsed.get("steps"), list) else []

        if verdict in {"correct", "incorrect"}:
            correct = verdict == "correct"
            if correct:
                result = {"correct": True, "message": "Correct", "steps": []}
            else:
                cleaned_steps = [str(step).strip() for step in steps if str(step).strip()]
                result = {
                    "correct": False,
                    "message": explanation or "Incorrect",
                    "steps": cleaned_steps[:6] if cleaned_steps else [
                        "Identify the incorrect logic or missing edge cases.",
                        "Adjust the algorithm to match required behavior.",
                        "Re-test with sample inputs and refine."
                    ]
                }

    return result or _fallback_grade(answer)


def _generate_guidance(answer: str) -> dict:
    prompt = (
        "You are a tutoring assistant. Provide a step-by-step walkthrough "
        "that explains how to build a solution without giving full code or pseudocode. "
        "Return ONLY valid JSON with this schema: "
        "{\"title\":string,\"steps\":string[]}\n"
        "Keep steps short, actionable, and avoid revealing a full solution."
    )

    gemini_text = _call_gemini(prompt, f"Student context:\n{answer}")
    if gemini_text:
        parsed = _extract_json(gemini_text)
        title = (parsed.get("title") or "Walkthrough").strip() or "Walkthrough"
        steps = parsed.get("steps") if isinstance(parsed.get("steps"), list) else []
        cleaned_steps = [
            _strip_code_blocks(str(step)).strip()
            for step in steps
            if str(step).strip()
        ]
        if cleaned_steps:
            durations = [7 for _ in cleaned_steps[:8]]
            return {"success": True, "title": title, "steps": cleaned_steps[:8], "durations": durations}

    fallback_steps = [
        "Identify the inputs, outputs, and any constraints.",
        "Break the task into smaller logical steps.",
        "Define the data structures you need for tracking progress.",
        "Write the main loop or flow that processes each step.",
        "Handle edge cases and invalid inputs.",
        "Test with small examples and refine."
    ]
    return {
        "success": True,
        "title": "Walkthrough",
        "steps": fallback_steps,
        "durations": [7 for _ in fallback_steps]
    }


def _chat_response(message: str, history: list) -> dict:
    lowered = message.lower()
    if "code example" in lowered or "full code" in lowered or "write the code" in lowered:
        return {
            "success": True,
            "reply": "I can’t share full code. I can guide you step-by-step or help debug a specific part. What’s the first step you’re unsure about?"
        }

    prompt = (
        "You are an interactive tutor helping a student write code. "
        "Do NOT provide full code or pseudocode. Ask clarifying questions and provide hints. "
        "Keep responses short and actionable."
    )

    history_text = ""
    for item in history[-6:]:
        role = (item.get("role") or "user").capitalize()
        content = item.get("content") or ""
        history_text += f"{role}: {content}\n"

    gemini_text = _call_gemini(prompt, f"Conversation:\n{history_text}\nUser: {message}")
    if gemini_text:
        return {"success": True, "reply": _strip_code_blocks(gemini_text).strip()}

    return {
        "success": True,
        "reply": "I can help with hints. What part of the logic is confusing?"
    }


def _get_earned_badges(player_id: int) -> list:
    badge_rows = (
        PlayerBadge.query
        .filter_by(player_id=player_id)
        .order_by(PlayerBadge.timestamp.asc())
        .all()
    )
    return [row.to_dict() for row in badge_rows]


@endgame_api.route("/player/<int:player_id>/score", methods=["GET"])
def get_player_score(player_id):
    player = Player.query.get(player_id)
    if not player:
        return jsonify({"success": False, "message": "Player not found"}), 404

    badge_rows = (
        PlayerBadge.query
        .filter_by(player_id=player_id)
        .order_by(PlayerBadge.timestamp.asc())
        .all()
    )

    earned_badges = [row.to_dict() for row in badge_rows]

    response = {
        "success": True,
        "player": player.to_dict(),
        "earned_badges": earned_badges,
        "attempts_by_badge": [
            {
                "badge_id": row.badge_id,
                "badge_name": row.badge.badge_name if row.badge else None,
                "attempts": row.attempts,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            }
            for row in badge_rows
        ],
        "completion_status": bool(player.completed_at),
        "final": {
            "completed_at": player.completed_at.isoformat() if player.completed_at else None,
            "final_attempts": player.final_attempts,
            "final_badge": None,
            "final_correct": player.final_correct,
        }
    }

    if player.final_badge_id:
        badge = Badge.query.get(player.final_badge_id)
        if badge:
            response["final"]["final_badge"] = badge.to_dict()

    return jsonify(response), 200


@endgame_api.route("/player/<int:player_id>/final-check", methods=["POST"])
def final_check(player_id):
    player = Player.query.get(player_id)
    if not player:
        return jsonify({"success": False, "message": "Player not found"}), 404

    data = _get_json()
    body_player_id = data.get("playerId")
    if body_player_id is not None and int(body_player_id) != int(player_id):
        return jsonify({"correct": False, "message": "playerId mismatch", "steps": []}), 400

    answer = (data.get("answer") or "").strip()
    if not answer:
        return jsonify({"correct": False, "message": "Answer is required", "steps": []}), 400

    max_len = 2000
    if len(answer) > max_len:
        answer = answer[:max_len]

    result = _grade_final_answer(answer)

    player.final_answer = answer
    player.final_correct = result["correct"]
    db.session.commit()

    return jsonify(result), 200


@endgame_api.route("/api/endgame/final-check", methods=["POST"])
def final_check_frontend():
    data = _get_json()
    answer = (data.get("answer") or "").strip()
    if not answer:
        return jsonify({"correct": False, "message": "Answer is required", "steps": []}), 400

    max_len = 2000
    if len(answer) > max_len:
        answer = answer[:max_len]

    player_id = data.get("playerId")
    player = None
    if player_id is not None:
        try:
            player = Player.query.get(int(player_id))
        except (TypeError, ValueError):
            return jsonify({"correct": False, "message": "Invalid playerId", "steps": []}), 400
        if not player:
            return jsonify({"correct": False, "message": "Player not found", "steps": []}), 404

    result = _grade_final_answer(answer)

    if player:
        player.final_answer = answer
        player.final_correct = result["correct"]
        db.session.commit()

    return jsonify(result), 200


@endgame_api.route("/player/<int:player_id>/final-badge", methods=["POST"])
def award_final_badge(player_id):
    player = Player.query.get(player_id)
    if not player:
        return jsonify({"success": False, "message": "Player not found"}), 404

    if not player.final_correct:
        return jsonify({"success": False, "message": "Final answer not correct"}), 400

    badge = Badge.query.filter_by(badge_name="Master").first()
    if not badge:
        badge = Badge(badge_name="Master")
        db.session.add(badge)
        db.session.commit()

    existing = PlayerBadge.query.filter_by(player_id=player_id, badge_id=badge.id).first()
    if not existing:
        attempts_value = player.final_attempts if player.final_attempts is not None else 0
        final_badge_row = PlayerBadge(
            player_id=player.id,
            badge_id=badge.id,
            attempts=attempts_value,
            timestamp=datetime.utcnow()
        )
        db.session.add(final_badge_row)
        db.session.commit()

    return jsonify({
        "success": True,
        "earned_badges": _get_earned_badges(player_id)
    }), 200


@endgame_api.route("/player/<int:player_id>/complete", methods=["POST"])
def complete_player(player_id):
    player = Player.query.get(player_id)
    if not player:
        return jsonify({"success": False, "message": "Player not found"}), 404

    data = _get_json()
    attempts = data.get("attempts")
    badge_id = data.get("badge_id")
    badge_name = data.get("badge_name")
    timestamp = _parse_iso(data.get("timestamp"))

    if attempts is None:
        return jsonify({"success": False, "message": "Missing attempts"}), 400

    if badge_id is None and badge_name:
        badge = Badge.query.filter_by(badge_name=badge_name).first()
        badge_id = badge.id if badge else None

    if badge_id is None:
        return jsonify({"success": False, "message": "Missing badge_id or badge_name"}), 400

    badge = Badge.query.get(badge_id)
    if not badge:
        return jsonify({"success": False, "message": "Badge not found"}), 404

    player.completed_at = timestamp or datetime.utcnow()
    player.final_attempts = attempts
    player.final_badge_id = badge_id

    final_badge_row = PlayerBadge(
        player_id=player.id,
        badge_id=badge_id,
        attempts=attempts,
        timestamp=timestamp or datetime.utcnow()
    )

    db.session.add(final_badge_row)
    db.session.commit()

    return jsonify({"success": True, "message": "Completion saved"}), 200


@endgame_api.route("/player/<int:player_id>/guidance", methods=["POST"])
def generate_guidance(player_id):
    player = Player.query.get(player_id)
    if not player:
        return jsonify({"success": False, "message": "Player not found"}), 404

    data = _get_json()
    answer = (data.get("answer") or "").strip()

    result = _generate_guidance(answer)
    return jsonify(result), 200


@endgame_api.route("/player/<int:player_id>/chat", methods=["POST"])
def chat_with_ai(player_id):
    player = Player.query.get(player_id)
    if not player:
        return jsonify({"success": False, "message": "Player not found"}), 404

    data = _get_json()
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "message": "Message is required"}), 400

    history = data.get("history") if isinstance(data.get("history"), list) else []

    result = _chat_response(message, history)
    return jsonify(result), 200


@endgame_api.route("/leaderboard", methods=["GET"])
def leaderboard():
    players = Player.query.all()
    payload = []

    for player in players:
        total_attempts = (
            db.session.query(db.func.sum(PlayerBadge.attempts))
            .filter(PlayerBadge.player_id == player.id)
            .scalar()
        ) or 0

        payload.append({
            "player": player.to_dict(),
            "total_attempts": total_attempts,
        })

    payload.sort(
        key=lambda item: (
            item["player"]["completed_at"] is None,
            item["player"]["completed_at"] or "",
            item["total_attempts"],
        )
    )

    return jsonify({"success": True, "leaderboard": payload}), 200
