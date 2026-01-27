# api/robop_api.py
"""
Robop API endpoints following your conventions:
- Blueprint registered in main file
- Uses jsonify + db model in model/robop_user.py
- Accepts BOTH old payload keys (GitHubID/Password) and new (id/password)
"""

from flask import Blueprint, request, jsonify, session
from model.robop_user import RobopUser
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

