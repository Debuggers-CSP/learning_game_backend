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


def _resolve_level(raw: str) -> str:
    raw = (raw or "").strip().lower()
    return LEVEL_MAP.get(raw, raw)


@pseudocode_bank_api.route("/random", methods=["GET"])
def random_question():
    """
    Examples:
      GET /api/pseudocode_bank/random?level=1
      GET /api/pseudocode_bank/random?level=super_easy
      GET /api/pseudocode_bank/random?level=hacker
    """
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
