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


# --- NEW: AUTOFILL ENDPOINT ---

@robop_api.route("/autofill", methods=["POST"])
def autofill_answer():
    """
    Returns the correct answer for a given sector and question.
    Request body: { "sector_id": 1-5, "question_num": 0-2 }
    Response: { "success": true, "answer": "..." }
    """
    data = _get_json()
    sector_id = data.get("sector_id")
    question_num = data.get("question_num")
    
    if sector_id is None or question_num is None:
        return jsonify({"success": False, "message": "Missing sector_id or question_num"}), 400
    
    # Define correct answers for each sector and question
    # Question 0: Robot Simulation Code
    # Question 1: Pseudocode Function
    # Question 2: MCQ Answer Index
    
    answers = {
        1: {
            0: "robot.MoveForward(4);\nrobot.TurnRight();\nrobot.MoveForward(4);",
            1: """function Average(nums) {
  let sum = 0;
  for (let n of nums) {
    sum += n;
  }
  return sum / nums.length;
}""",
            2: 0  # "13" is the correct answer for "1101 binary?"
        },
        2: {
            0: "robot.MoveForward(4);\nrobot.TurnLeft();\nrobot.MoveForward(4);",
            1: """function CountAbove(nums, t) {
  let count = 0;
  for (let n of nums) {
    if (n > t) {
      count += 1;
    }
  }
  return count;
}""",
            2: 0  # "Both" is correct for AND logic
        },
        3: {
            0: "robot.MoveForward(2);\nrobot.TurnRight();\nrobot.MoveForward(4);\nrobot.TurnRight();\nrobot.MoveForward(2);",
            1: """function MaxValue(nums) {
  let max = nums[0];
  for (let n of nums) {
    if (n > max) {
      max = n;
    }
  }
  return max;
}""",
            2: 0  # "Hide detail" is correct for abstraction
        },
        4: {
            0: "robot.MoveForward(4);",
            1: """function ReplaceAll(list, t, r) {
  for (let i=0; i<list.length; i++) {
    if (list[i] === t) {
      list[i] = r;
    }
  }
  return list;
}""",
            2: 0  # "Routing" is correct for IP Protocol
        },
        5: {
            0: "robot.TurnRight();\nrobot.MoveForward(2);\nrobot.TurnLeft();\nrobot.MoveForward(4);\nrobot.TurnLeft();\nrobot.MoveForward(2);",
            1: """function GetEvens(nums) {
  let evens = [];
  for (let n of nums) {
    if (n % 2 === 0) {
      evens.push(n);
    }
  }
  return evens;
}""",
            2: 0  # "Rule of thumb" is correct for heuristics
        }
    }
    
    # Check if sector and question exist
    if sector_id not in answers or question_num not in answers[sector_id]:
        return jsonify({"success": False, "message": "Invalid sector or question number"}), 404
    
    answer = answers[sector_id][question_num]
    
    return jsonify({
        "success": True,
        "answer": answer,
        "sector_id": sector_id,
        "question_num": question_num
    }), 200