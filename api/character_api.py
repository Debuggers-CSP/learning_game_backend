from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# -------------------------
# APP SETUP
# -------------------------

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # change later

# Allow frontend requests (Jekyll localhost:4500)
CORS(app, supports_credentials=True)

# -------------------------
# DATABASE CONFIG
# -------------------------

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///players.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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
# TEST LOGIN ROUTE
# (Creates a session user)
# -------------------------

@app.route("/api/test_login", methods=["POST"])
def test_login():
    """
    This simulates login so session exists.
    Use this once before updating character.
    """

    data = request.get_json()
    uid = data.get("uid")

    if not uid:
        return jsonify({"success": False, "message": "UID required"}), 400

    # Create user if not exists
    user = RobopUser.query.filter_by(_uid=uid).first()
    if not user:
        user = RobopUser(_uid=uid)
        db.session.add(user)
        db.session.commit()

    session["robop_uid"] = uid

    return jsonify({
        "success": True,
        "message": "Session created",
        "uid": uid
    })

# -------------------------
# CHARACTER UPDATE ROUTE
# -------------------------

@app.route("/api/update_character", methods=["POST"])
def update_character():

    # 🔐 AUTH CHECK
    uid = session.get("robop_uid")
    if not uid:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    # 📥 INPUT
    data = request.get_json()
    character_name = data.get("name")
    character_class = data.get("class")

    # 🛑 VALIDATION
    if not character_name or not character_class:
        return jsonify({
            "success": False,
            "message": "Missing name or class"
        }), 400

    # 🧠 PROCESS
    user = RobopUser.query.filter_by(_uid=uid).first()
    if not user:
        return jsonify({
            "success": False,
            "message": "User not found"
        }), 404

    user._character_name = character_name
    user._character_class = character_class

    db.session.commit()

    # 📤 OUTPUT
    return jsonify({
        "success": True,
        "message": "Character saved",
        "character": user.to_dict()
    })

# -------------------------
# OPTIONAL: GET USER DATA
# -------------------------

@app.route("/api/get_character", methods=["GET"])
def get_character():

    uid = session.get("robop_uid")
    if not uid:
        return jsonify({"success": False}), 401

    user = RobopUser.query.filter_by(_uid=uid).first()

    return jsonify({
        "success": True,
        "character": user.to_dict()
    })

# -------------------------
# RUN SERVER
# -------------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="127.0.0.1", port=8320, debug=True)
