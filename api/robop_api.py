# api/robop_api.py

from flask import Blueprint, request, jsonify, session
from model.robop_user import RobopUser, BadgeThreshold, UserBadge, StationHint
from datetime import datetime
import requests
import json

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


# --- NEW: AI HINT GENERATION FUNCTIONS ---

def call_ai_api(question_text):
    """Calls an AI API to generate hints for a given question."""
    # IMPORTANT: Replace with your actual API key
    api_key = "YOUR API KEY HERE"
    
    # You can choose between Groq or OpenAI
    # Option 1: Groq API
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    # Logic: Ask AI to help with the specific question
    prompt = f"Provide a list of 3 short hints for the following programming question. Each hint should be a single concise sentence. Return ONLY a JSON array of strings, nothing else.\n\nQuestion: {question_text}"
    
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 150
            },
            timeout=10  # Timeout after 10 seconds
        )
        
        if response.status_code != 200:
            # Fallback to mock hints if API fails
            return ["Think about the steps needed to solve this problem.", 
                   "Consider edge cases in your solution.", 
                   "Review similar examples you've seen before."]
        
        # Try to parse the response as JSON
        content = response.json()["choices"][0]["message"]["content"].strip()
        
        # Clean up the response (sometimes LLMs add extra text)
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse the JSON list
        hints = json.loads(content)
        
        # Ensure we have exactly 3 hints
        if isinstance(hints, list) and len(hints) >= 3:
            return hints[:3]
        else:
            # Fallback
            return ["Break the problem into smaller parts.", 
                   "Think about the expected output format.", 
                   "Try to explain the solution in your own words first."]
    
    except Exception as e:
        # If API call fails, return default hints
        print(f"AI API Error: {e}")
        return ["Consider the input requirements.", 
               "Think about the algorithm steps.", 
               "Test your solution with sample inputs."]


# --- NEW: GET HINT ENDPOINT (USING SELECTION) ---

@robop_api.route("/get_hint", methods=["POST"])
def get_hint():
    """
    Uses SELECTION (if/else) to decide whether to fetch from DB or trigger AI.
    Request body: { "module_key": "s1_m0", "question": "...", "attempt": 0-2 }
    Response: { "success": true, "hint": "..." }
    """
    data = _get_json()
    key = data.get("module_key")
    q_text = data.get("question")  # Grabs the question from the screen
    idx = data.get("attempt")
    
    if not key or not q_text or idx is None:
        return jsonify({
            "success": False,
            "message": "Missing module_key, question, or attempt index"
        }), 400
    
    # SELECTION: Check if we have already saved these hints in our List
    entry = StationHint.query.filter_by(module_key=key).first()
    
    if not entry:
        # If not in DB, call the 3rd Party AI Procedure
        new_hints = call_ai_api(q_text)
        entry = StationHint(key=key, hints=new_hints)
        db.session.add(entry)
        db.session.commit()
    
    # Check if attempt index is valid
    if idx < 0 or idx >= len(entry.hint_collection):
        return jsonify({
            "success": False,
            "message": f"Invalid attempt index. Must be between 0 and {len(entry.hint_collection)-1}"
        }), 400
    
    # Output the specific hint requested
    return jsonify({
        "success": True,
        "hint": entry.hint_collection[idx],
        "module_key": key,
        "attempt": idx,
        "total_hints": len(entry.hint_collection)
    })


@robop_api.route("/generate_hints", methods=["POST"])
def generate_hints():
    """
    Generates AI hints for a question and stores them in the database.
    Request body: { "module_key": "s1_m0", "question_text": "..." }
    Response: { "success": true, "hints": ["hint1", "hint2", "hint3"] }
    """
    data = _get_json()
    module_key = data.get("module_key")
    question_text = data.get("question_text")
    
    if not module_key or not question_text:
        return jsonify({
            "success": False, 
            "message": "Missing module_key or question_text"
        }), 400
    
    # Check if hints already exist for this module
    existing = StationHint.query.filter_by(module_key=module_key).first()
    if existing:
        # Return existing hints from database
        return jsonify({
            "success": True,
            "hints": existing.hint_collection,
            "cached": True
        }), 200
    
    # Generate new hints using AI
    try:
        hint_list = call_ai_api(question_text)
        new_entry = StationHint(key=module_key, hints=hint_list)
        db.session.add(new_entry)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "hints": hint_list,
            "cached": False
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Failed to generate hints: {str(e)}"
        }), 500