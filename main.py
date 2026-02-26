# imports from flask
from datetime import datetime
from urllib.parse import urljoin, urlparse
import os
import requests
import socket

from flask import (
    abort, redirect, render_template, request, send_from_directory,
    url_for, jsonify, current_app, g
)
from flask_login import current_user, login_user, logout_user, login_required
from flask.cli import AppGroup
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from api.jwt_authorize import token_required

# ✅ CORS
from flask_cors import CORS

# import "objects" from "this" project
from __init__ import app, db, login_manager  # Key Flask objects
# API endpoints
from api.user import user_api
from api.python_exec_api import python_exec_api
from api.javascript_exec_api import javascript_exec_api
from api.section import section_api
from api.persona_api import persona_api
from api.pfp import pfp_api
from api.analytics import analytics_api
from api.student import student_api
from api.groq_api import groq_api
from api.chatgpt_api import chatgpt_api
from api.microblog_api import microblog_api
from api.classroom_api import classroom_api
from api.data_export_import_api import data_export_import_api
from hacks.joke import joke_api  # Import the joke API blueprint
from api.post import post_api  # Import the social media post API
# from api.announcement import announcement_api ##temporary revert
from api.pseudocode_bank_api import pseudocode_bank_api
from model.pseudocode_bank import initPseudocodeQuestionBank
from api.character_api import character_api
from api.pseudocodeanswer_bank_api import pseudocodeanswer_bank_api
from model.pseudocodeanswer_bank import initPseudocodeAnswerBank

# database Initialization functions
from model.user import User, initUsers
from model.user import Section
from model.github import GitHubUser
from model.feedback import Feedback
from api.analytics import get_date_range
# from api.grade_api import grade_api
from api.study import study_api
from api.feedback_api import feedback_api
from model.study import Study, initStudies
from model.classroom import Classroom
from model.persona import Persona, initPersonas, initPersonaUsers
from model.post import Post, init_posts
from model.microblog import MicroBlog, Topic, initMicroblogs
from hacks.jokes import initJokes
from api.robop_api import robop_api
from model.robop_user import RobopUser, UserBadge, initRobopUsers
from api.endgame_api import endgame_api
from api.debug_challenge_api import debug_challenge_api
from model.endgame import init_endgame_data
from model.debug_challenge import init_debug_challenge_data

# Load environment variables
load_dotenv()

app.config['KASM_SERVER'] = os.getenv('KASM_SERVER')
app.config['KASM_API_KEY'] = os.getenv('KASM_API_KEY')
app.config['KASM_API_KEY_SECRET'] = os.getenv('KASM_API_KEY_SECRET')

# =========================================================
# ✅ CORS SETUP
# Allow your frontend at http://localhost:4500
# =========================================================
allowed_origins = [
    "http://localhost:4500",
    "http://127.0.0.1:4500",
]

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

# register URIs for api endpoints
app.register_blueprint(python_exec_api)
app.register_blueprint(javascript_exec_api)
app.register_blueprint(user_api)
app.register_blueprint(section_api)
app.register_blueprint(persona_api)
app.register_blueprint(pfp_api)
app.register_blueprint(groq_api)
app.register_blueprint(chatgpt_api)
app.register_blueprint(microblog_api)

app.register_blueprint(analytics_api)
app.register_blueprint(student_api)
# app.register_blueprint(grade_api)
app.register_blueprint(study_api)
app.register_blueprint(classroom_api)
app.register_blueprint(feedback_api)
app.register_blueprint(data_export_import_api)
app.register_blueprint(joke_api)
app.register_blueprint(post_api)
app.register_blueprint(robop_api)
app.register_blueprint(endgame_api)
app.register_blueprint(debug_challenge_api)
# app.register_blueprint(announcement_api) ##temporary revert
#app.register_blueprint(pseudocode_bank_api)
app.register_blueprint(pseudocodeanswer_bank_api)
app.register_blueprint(character_api)

# Jokes file initialization
with app.app_context():
    initJokes()
    initRobopUsers()
    init_endgame_data()
    initPseudocodeQuestionBank(force_recreate=True)
    initPseudocodeAnswerBank(force_recreate=True)
    init_debug_challenge_data()

login_manager.login_view = "login"

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect(url_for('login', next=request.path))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    next_page = request.args.get('next', '') or request.form.get('next', '')
    if request.method == 'POST':
        user = User.query.filter_by(_uid=request.form['username']).first()
        if user and user.is_password(request.form['password']):
            login_user(user)
            if not is_safe_url(next_page):
                return abort(400)
            return redirect(next_page or url_for('index'))
        else:
            error = 'Invalid username or password.'
    return render_template("login.html", error=error, next=next_page)

@app.route('/studytracker')
def studytracker():
    return render_template("studytracker.html")

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/')
def index():
    print("Home:", current_user)
    return render_template("index.html")

@app.route('/ending/<int:player_id>')
def ending_page(player_id):
    api_base = os.getenv("PUBLIC_API_BASE", "").strip()
    if not api_base:
        api_base = request.host_url.rstrip("/")
    return render_template("ending.html", player_id=player_id, api_base=api_base)

@app.route('/debug-challenge')
def debug_challenge_page():
    return render_template("debug_challenge.html")

@app.route('/debug')
def debug_challenge_alias():
    return render_template("debug_challenge.html")

@app.route('/socket.io/', defaults={'path': ''}, methods=['GET', 'POST', 'OPTIONS'])
@app.route('/socket.io/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def socket_io_stub(path=''):
    return '', 200

@app.route('/users/table2')
@login_required
def u2table():
    users = User.query.all()
    return render_template("u2table.html", user_data=users)

@app.route('/sections/')
@login_required
def sections():
    sections = Section.query.all()
    return render_template("sections.html", sections=sections)

@app.route('/persona/')
@login_required
def persona():
    personas = Persona.query.all()
    return render_template("persona.html", personas=personas)

@app.route("/robop/api/users", methods=["GET"])
def get_robop_users_api():
    try:
        users = RobopUser.query.order_by(RobopUser.id.asc()).all()
        users_data = []
        for u in users:
            users_data.append({
                "id": u.id,
                "uid": u.uid,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": getattr(u, 'email', None),
                "role": getattr(u, 'role', 'user'),
                "status": getattr(u, 'status', 'active'),
                "created": u._created.isoformat() if hasattr(u, "_created") and u._created else None,
                "last_login": u._last_login.isoformat() if hasattr(u, "_last_login") and u._last_login else None,
            })
        return jsonify({"success": True, "data": users_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/robop/api/users/<int:user_id>", methods=["PUT"])
def update_robop_user(user_id):
    try:
        user = RobopUser.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        data = request.get_json() or {}

        if 'uid' in data:
            user.uid = data['uid']
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if hasattr(user, "email") and 'email' in data: user.email = data['email']
        if hasattr(user, "role") and 'role' in data: user.role = data['role']
        if hasattr(user, "status") and 'status' in data: user.status = data['status']
        
        db.session.commit()
        return jsonify({"success": True, "message": "User updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/robop/api/users/<int:user_id>", methods=["DELETE"])
def delete_robop_user(user_id):
    try:
        user = RobopUser.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True, "message": "User deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/robop/api/users", methods=["POST"])
def add_robop_user():
    try:
        data = request.get_json() or {}

        required_fields = ["uid", "first_name", "last_name"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"success": False, "error": f"{field} is required"}), 400

        # IMPORTANT: use _uid because your column is _uid
        existing_user = RobopUser.query.filter_by(_uid=data["uid"]).first()
        if existing_user:
            return jsonify({"success": False, "error": "User ID already exists"}), 400

        # If your constructor requires password, give a default one
        new_user = RobopUser(
            uid=data["uid"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            password="default123"  # or generate_password_hash("default123") if needed
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "User added successfully",
            "user_id": new_user.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/robop/users")
def robop_users():
    users = RobopUser.query.order_by(RobopUser.id.asc()).all()

    # Badge tier ranking (higher = better)
    # Anything unknown (like "Seed Badge") becomes 0
    BADGE_RANK = {
        "Gold": 4,
        "Silver": 3,
        "Bronze": 2,
        "Participant": 1,
    }

    def badge_rank(name: str) -> int:
        return BADGE_RANK.get((name or "").strip(), 0)

    def best_badge_key(ub: UserBadge):
        """
        Sort key where "best" means:
        - Higher badge tier is better
        - Fewer attempts is better
        - Not using autofill is better
        - More recent is better
        """
        tier = badge_rank(getattr(ub, "_badge_name", ""))
        attempts = getattr(ub, "_attempts", 10**9)
        used_autofill = bool(getattr(ub, "_used_autofill", False))
        dt = getattr(ub, "_date_earned", None) or datetime.min

        # We want max() by this key, so keep "good" values higher:
        # -tier? No, tier already higher is better
        # -attempts: fewer is better -> invert attempts
        # used_autofill: False better -> invert to 1/0
        return (tier, -attempts, 0 if used_autofill else 1, dt)

    robop_user_data = []

    for u in users:
        # Use relationship if available; otherwise fall back to query
        badges = list(getattr(u, "badges", []) or [])
        badges.sort(key=lambda b: getattr(b, "_date_earned", datetime.min), reverse=True)

        badge_count = len(badges)
        last_earned = badges[0] if badges else None
        best_badge = max(badges, key=best_badge_key) if badges else None

        robop_user_data.append({
            "id": u.id,
            "uid": u.uid,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "created": u._created.isoformat() if getattr(u, "_created", None) else None,
            "last_login": u._last_login.isoformat() if getattr(u, "_last_login", None) else None,

            "badge_count": badge_count,

            # best badge details
            "best_badge": best_badge._badge_name if best_badge else None,
            "best_sector": best_badge._sector_id if best_badge else None,
            "best_module": best_badge._module_id if best_badge else None,
            "best_attempts": best_badge._attempts if best_badge else None,
            "best_used_autofill": best_badge._used_autofill if best_badge else None,
            "best_earned": best_badge._date_earned.isoformat() if best_badge and best_badge._date_earned else None,

            # last earned details
            "last_badge": last_earned._badge_name if last_earned else None,
            "last_earned": last_earned._date_earned.isoformat() if last_earned and last_earned._date_earned else None,
        })

    return render_template("robop_users.html", robop_user_data=robop_user_data)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@app.route('/users/delete/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.delete()
        return jsonify({'message': 'User deleted successfully'}), 200
    return jsonify({'error': 'User not found'}), 404

@app.route('/users/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.update({"password": app.config['DEFAULT_PASSWORD']}):
        return jsonify({'message': 'Password reset successfully'}), 200
    return jsonify({'error': 'Password reset failed'}), 500

# Create an AppGroup for custom commands
custom_cli = AppGroup('custom', help='Custom commands')

@custom_cli.command('generate_data')
def generate_data():
    initUsers()
    initMicroblogs()
    initPersonas()
    initPersonaUsers()

app.cli.add_command(custom_cli)

# ✅ Run server on a stable port (frontend expects 8320)
if __name__ == "__main__":
    host = "0.0.0.0"
    try:
        port = int(os.environ.get("FLASK_PORT", 8320))
    except Exception:
        port = 8320

    print(f"** Server running: http://localhost:{port}")
    debug_mode = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes", "on")
    app.run(debug=debug_mode, host=host, port=port, use_reloader=False)