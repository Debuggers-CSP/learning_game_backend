from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# -------------------------
# APP SETUP
# -------------------------

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

# Allow frontend requests with credentials
CORS(app, 
     origins=["http://localhost:4000", "http://127.0.0.1:4000"],
     supports_credentials=True,
     allow_headers=["Content-Type"],
     methods=["GET", "POST", "OPTIONS"])

# -------------------------
# DATABASE CONFIG
# -------------------------

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///players.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = False  # Set to True if using HTTPS

db = SQLAlchemy(app)

# -------------------------
# DATABASE MODEL
# -------------------------

class RobopUser(db.Model):
    __tablename__ = "robop_users"

    _uid = db.Column(db.String, primary_key=True)
    _character_name = db.Column(db.String(64), nullable=True)
    _character_class = db.Column(db.String(64), nullable=True)

    def to_dict(self):
        return {
            "uid": self._uid,
            "character_name": self._character_name,
            "character_class": self._character_class
        }

# -------------------------
# UPDATED CHARACTER ROUTE
# (Auto-creates session if needed)
# -------------------------

@app.route("/api/update_character", methods=["POST", "OPTIONS"])
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
        import time
        import random
        uid = f"player_{int(time.time())}_{random.randint(1000, 9999)}"
        session["robop_uid"] = uid

    # 🧠 PROCESS - Get or create user
    user = RobopUser.query.filter_by(_uid=uid).first()
    if not user:
        user = RobopUser(_uid=uid)
        db.session.add(user)

    user._character_name = character_name
    user._character_class = character_class

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Database error: {str(e)}"
        }), 500

    # 📤 OUTPUT
    return jsonify({
        "success": True,
        "message": "Character saved",
        "player": user.to_dict()
    })

# -------------------------
# GET CHARACTER DATA
# -------------------------

@app.route("/api/get_character", methods=["GET"])
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
        "character": user.to_dict()
    })

# -------------------------
# HEALTH CHECK
# -------------------------

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "success": True,
        "message": "Server is running",
        "session_active": "robop_uid" in session
    })

# -------------------------
# RUN SERVER
# -------------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✓ Database tables created")
        print("✓ Server running on http://127.0.0.1:8320")

    app.run(host="127.0.0.1", port=8320, debug=True)