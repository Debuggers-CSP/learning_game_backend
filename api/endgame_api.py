from datetime import datetime

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
    answer = data.get("answer", "")

    expected = current_app.config.get("FINAL_CODE_ANSWER", "")
    normalized_answer = _normalize_answer(answer)
    normalized_expected = _normalize_answer(expected)
    correct = bool(normalized_expected) and normalized_answer == normalized_expected

    player.final_answer = answer
    player.final_correct = correct
    db.session.commit()

    return jsonify({"correct": correct}), 200


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
