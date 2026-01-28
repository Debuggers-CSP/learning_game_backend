# api/robop_api.py

from flask import Blueprint, request, jsonify, session
from model.robop_user import RobopUser, BadgeThreshold, UserBadge
from datetime import datetime

from __init__ import db

robop_api = Blueprint("robop_api", __name__, url_prefix="/api/robop")


def _get_json():
    return request.get_json(silent=True) or {}


def _pick(data, *keys, default=None):
    for k in keys:
        if k in data and data[k] is not None:
            return data[k]
    return default


@robop_api.route("/register", methods=["POST"])
def register():
    data = _get_json()

    uid = (_pick(data, "id", "uid", "GitHubID", "githubId") or "").strip()
    password = _pick(data, "password", "Password") or ""
    first_name = (_pick(data, "first_name", "FirstName") or "").strip()
    last_name = (_pick(data, "last_name", "LastName") or "").strip()

    if not uid or not password or not first_name or not last_name:
        return jsonify({
            "success": False,
            "message": "Missing required fields: id, password, first_name, last_name."
        }), 400

    if RobopUser.query.filter_by(_uid=uid).first():
        return jsonify({
            "success": False,
            "message": "User already exists. Please login."
        }), 409

    try:
        user = RobopUser(uid=uid, first_name=first_name, last_name=last_name, password=password)
        user.create()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Registration failed.",
            "error": str(e)
        }), 500

    return jsonify({
        "success": True,
        "message": "Registered successfully.",
        "user": user.to_dict()
    }), 201


@robop_api.route("/login", methods=["POST"])
def login():
    data = _get_json()

    uid = (_pick(data, "id", "uid", "GitHubID", "githubId") or "").strip()
    password = _pick(data, "password", "Password") or ""

    if not uid or not password:
        return jsonify({
            "success": False,
            "message": "Missing required fields: id and password."
        }), 400

    user = RobopUser.query.filter_by(_uid=uid).first()
    if not user or not user.is_password(password):
        return jsonify({
            "success": False,
            "message": "Invalid credentials."
        }), 401

    # Server session (optional, but useful)
    session["robop_uid"] = user.uid
    user.touch_login()

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": user.to_dict()
    }), 200


@robop_api.route("/logout", methods=["POST"])
def logout():
    session.pop("robop_uid", None)
    return jsonify({"success": True, "message": "Logged out."}), 200


@robop_api.route("/me", methods=["GET"])
def me():
    uid = session.get("robop_uid")
    if not uid:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    user = RobopUser.query.filter_by(_uid=uid).first()
    if not user:
        session.pop("robop_uid", None)
        return jsonify({"success": False, "message": "Session invalid."}), 401

    return jsonify({"success": True, "user": user.to_dict()}), 200


# --- APPENDED: NEW BADGE ROUTES ---

@robop_api.route("/badge_thresholds", methods=["GET"])
def get_thresholds():
    """Returns the list of badge criteria for the frontend to loop through."""
    thresholds = BadgeThreshold.query.order_by(BadgeThreshold._threshold.desc()).all()
    return jsonify([t.to_dict() for t in thresholds]), 200


@robop_api.route("/assign_badge", methods=["POST"])
def assign_badge():
    """Saves an earned badge to the database for the logged-in user."""
    uid = session.get("robop_uid")
    if not uid:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    user = RobopUser.query.filter_by(_uid=uid).first()
    data = _get_json()
    
    sector_id = data.get("sector_id")
    score = data.get("score")
    badge_name = data.get("badge_name")

    if sector_id is None or score is None or not badge_name:
        return jsonify({"success": False, "message": "Missing badge data"}), 400

    try:
        new_badge = UserBadge(user_id=user.id, sector_id=sector_id, score=score, badge_name=badge_name)
        db.session.add(new_badge)
        db.session.commit()
        return jsonify({"success": True, "message": f"Badge '{badge_name}' saved!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500