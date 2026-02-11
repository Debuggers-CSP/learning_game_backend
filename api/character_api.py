from flask import Blueprint, request, jsonify, session
from model.robop_user import RobopUser
from __init__ import db
import time
import random

# Create Blueprint
character_api = Blueprint('character_api', __name__, url_prefix='/api')

# -------------------------
# UPDATE CHARACTER ROUTE
# -------------------------

@character_api.route("/update_character", methods=["POST", "OPTIONS"])
def update_character():
    # Handle preflight request
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    # 📥 INPUT
    data = request.get_json()
    character_name = data.get("name")
    character_class = data.get("class")

    # 🛑 VALIDATION
    if not character_name or not character_class:
        return jsonify({
            "success": False,
            "error": "Missing name or class"
        }), 400

    # 🔐 GET OR CREATE SESSION
    uid = session.get("robop_uid")
    
    # If no session exists, create one with a new UID
    if not uid:
        uid = f"player_{int(time.time())}_{random.randint(1000, 9999)}"
        session["robop_uid"] = uid
        print(f"Created new session with UID: {uid}")

    # 🧠 PROCESS - Get or create user
    user = RobopUser.query.filter_by(_uid=uid).first()
    if not user:
        # Create new user with character info
        user = RobopUser(
            uid=uid,
            first_name=character_name,
            last_name=character_class,
            password="temporary_password"
        )
        db.session.add(user)
        print(f"Created new user: {uid}")
    else:
        # Update existing user
        user.first_name = character_name
        user.last_name = character_class
        print(f"Updated existing user: {uid}")

    try:
        db.session.commit()
        print(f"Database committed successfully for {uid}")
    except Exception as e:
        db.session.rollback()
        print(f"Database error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Database error: {str(e)}"
        }), 500

    # 📤 OUTPUT
    return jsonify({
        "success": True,
        "message": "Character saved",
        "player": {
            "uid": user.uid,
            "character_name": character_name,
            "character_class": character_class
        }
    })

# -------------------------
# GET CHARACTER DATA
# -------------------------

@character_api.route("/get_character", methods=["GET"])
def get_character():
    uid = session.get("robop_uid")
    
    if not uid:
        return jsonify({
            "success": False,
            "error": "No session found"
        }), 401

    user = RobopUser.query.filter_by(_uid=uid).first()
    
    if not user:
        return jsonify({
            "success": False,
            "error": "User not found"
        }), 404

    return jsonify({
        "success": True,
        "character": {
            "uid": user.uid,
            "character_name": user.first_name,
            "character_class": user.last_name
        }
    })