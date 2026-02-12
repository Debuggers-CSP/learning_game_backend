# imports from flask
from datetime import datetime
from urllib.parse import urljoin, urlparse
import os
import requests

from flask import (
    abort, redirect, render_template, request, send_from_directory,
    url_for, jsonify, current_app, g
)
from flask_login import current_user, login_user, logout_user, login_required
from flask.cli import AppGroup
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from api.jwt_authorize import token_required

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
#from api.announcement import announcement_api ##temporary revert
from api.pseudocode_bank_api import pseudocode_bank_api
from model.pseudocode_bank import initPseudocodeQuestionBank
from api.character_api import character_api

# database Initialization functions
from model.user import User, initUsers
from model.user import Section;
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


# from model.announcement import Announcement ##temporary revert

# server only Views

# Load environment variables
load_dotenv()

app.config['KASM_SERVER'] = os.getenv('KASM_SERVER')
app.config['KASM_API_KEY'] = os.getenv('KASM_API_KEY')
app.config['KASM_API_KEY_SECRET'] = os.getenv('KASM_API_KEY_SECRET')



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
app.register_blueprint(data_export_import_api)  # Register the data export/import API
app.register_blueprint(joke_api)  # Register the joke API blueprint
app.register_blueprint(post_api)  # Register the social media post API
app.register_blueprint(robop_api)
app.register_blueprint(endgame_api)
app.register_blueprint(debug_challenge_api)
# app.register_blueprint(announcement_api) ##temporary revert
app.register_blueprint(pseudocode_bank_api)
app.register_blueprint(character_api)

# Jokes file initialization
with app.app_context():
    initJokes()
    initRobopUsers()
    init_endgame_data()
    initPseudocodeQuestionBank()
    init_debug_challenge_data()
# Tell Flask-Login the view function name of your login route
login_manager.login_view = "login"

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect(url_for('login', next=request.path))

# register URIs for server pages
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Helper function to check if the URL is safe for redirects
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

@app.route('/studytracker')  # route for the study tracker page
def studytracker():
    return render_template("studytracker.html")
    
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.errorhandler(404)  # catch for URL not found
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

@app.route('/')  # connects default URL to index() function
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
    """API to get all Robop users data"""
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
    """API to update Robop user information"""
    try:
        user = RobopUser.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        
        data = request.get_json()
        
        # Update fields if provided
        if 'uid' in data:
            user.uid = data['uid']
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'email' in data:
            user.email = data['email']
        if 'role' in data:
            user.role = data['role']
        if 'status' in data:
            user.status = data['status']
        
        db.session.commit()
        return jsonify({"success": True, "message": "User updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/robop/api/users/<int:user_id>", methods=["DELETE"])
def delete_robop_user(user_id):
    """API to delete a Robop user"""
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
    """API to add a new Robop user"""
    try:
        data = request.get_json()
        
        # Check required fields
        required_fields = ["uid", "first_name", "last_name"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"success": False, "error": f"{field} is required"}), 400
        
        # Check if user already exists
        existing_user = RobopUser.query.filter_by(uid=data["uid"]).first()
        if existing_user:
            return jsonify({"success": False, "error": "User ID already exists"}), 400
        
        # Create new user
        new_user = RobopUser(
            uid=data["uid"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data.get("email"),
            role=data.get("role", "user"),
            status=data.get("status", "active")
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

    robop_user_data = []
    for u in users:
        # pull all badges for this user once
        badges = (
            UserBadge.query
            .filter_by(user_id=u.id)
            .order_by(UserBadge._date_earned.desc())
            .all()
        )

        badge_count = len(badges)

        # "best" badge = highest score (tie-breaker: most recently earned)
        best_badge = None
        if badges:
            best_badge = sorted(
                badges,
                key=lambda b: (b._score, b._date_earned),
                reverse=True
            )[0]

        # last earned badge (most recent by date)
        last_earned = badges[0] if badges else None

        robop_user_data.append({
            "id": u.id,
            "uid": u.uid,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "created": u._created.isoformat() if getattr(u, "_created", None) else None,
            "last_login": u._last_login.isoformat() if getattr(u, "_last_login", None) else None,

            # NEW badge fields
            "badge_count": badge_count,
            "best_badge": best_badge._badge_name if best_badge else None,
            "best_score": best_badge._score if best_badge else None,
            "best_sector": best_badge._sector_id if best_badge else None,
            "last_badge": last_earned._badge_name if last_earned else None,
            "last_earned": last_earned._date_earned.isoformat() if last_earned else None,
        })

    return render_template("robop_users.html", robop_user_data=robop_user_data)


# Helper function to extract uploads for a user (ie PFP image)
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

    # Set the new password
    if user.update({"password": app.config['DEFAULT_PASSWORD']}):
        return jsonify({'message': 'Password reset successfully'}), 200
    return jsonify({'error': 'Password reset failed'}), 500

@app.route('/kasm_users')
def kasm_users():
    # Fetch configuration details from environment or app config
    SERVER = current_app.config.get('KASM_SERVER')
    API_KEY = current_app.config.get('KASM_API_KEY')
    API_KEY_SECRET = current_app.config.get('KASM_API_KEY_SECRET')

    # Validate required configurations
    if not SERVER or not API_KEY or not API_KEY_SECRET:
        return render_template('error.html', message='KASM keys are missing'), 400

    try:
        # Prepare API request details
        url = f"{SERVER}/api/public/get_users"
        data = {
            "api_key": API_KEY,
            "api_key_secret": API_KEY_SECRET
        }

        # Perform the POST request
        response = requests.post(url, json=data, timeout=10)  # Added timeout for reliability

        # Validate the API response
        if response.status_code != 200:
            return render_template(
                'error.html', 
                message='Failed to get users', 
                code=response.status_code
            ), response.status_code

        # Parse the users list from the response
        users = response.json().get('users', [])

        # Process `last_session` and handle potential parsing issues
        for user in users:
            last_session = user.get('last_session')
            try:
                user['last_session'] = datetime.fromisoformat(last_session) if last_session else None
            except ValueError:
                user['last_session'] = None  # Fallback for invalid date formats

        # Sort users by `last_session`, treating `None` as the oldest date
        sorted_users = sorted(
            users, 
            key=lambda x: x['last_session'] or datetime.min, 
            reverse=True
        )

        # Render the sorted users in the template
        return render_template('kasm_users.html', users=sorted_users)

    except requests.RequestException as e:
        # Handle connection errors or other request exceptions
        return render_template(
            'error.html', 
            message=f"Error connecting to KASM API: {str(e)}"
        ), 500
        
        
@app.route('/delete_user/<user_id>', methods=['DELETE'])
def delete_user_kasm(user_id):
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    SERVER = current_app.config.get('KASM_SERVER')
    API_KEY = current_app.config.get('KASM_API_KEY')
    API_KEY_SECRET = current_app.config.get('KASM_API_KEY_SECRET')

    if not SERVER or not API_KEY or not API_KEY_SECRET:
        return {'message': 'KASM keys are missing'}, 400

    try:
        # Kasm API to delete a user
        url = f"{SERVER}/api/public/delete_user"
        data = {
            "api_key": API_KEY,
            "api_key_secret": API_KEY_SECRET,
            "target_user": {"user_id": user_id},
            "force": False
        }
        response = requests.post(url, json=data)

        if response.status_code == 200:
            return {'message': 'User deleted successfully'}, 200
        else:
            return {'message': 'Failed to delete user'}, response.status_code

    except requests.RequestException as e:
        return {'message': 'Error connecting to KASM API', 'error': str(e)}, 500

# ==================== BADGE EDIT API  ====================

@app.route("/robop/api/users/<int:user_id>/update_badge", methods=["PUT"])
def update_user_badge_info(user_id):
    """API to update user's badge information (direct update of best/last badges)"""
    try:
        user = RobopUser.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        
        data = request.get_json()
        print(f"Updating badge info for user {user_id}: {data}")
        
        badges = UserBadge.query.filter_by(user_id=user_id).order_by(UserBadge._date_earned.desc()).all()
        
        if not badges:
            return jsonify({"success": False, "error": "No badges found for this user"}), 404
        
        if 'best_badge' in data or 'best_score' in data or 'best_sector' in data:
            best_badge = sorted(
                badges,
                key=lambda b: (b._score, b._date_earned),
                reverse=True
            )[0]
            
            if 'best_badge' in data:
                best_badge._badge_name = data['best_badge']
            if 'best_score' in data:
                best_badge._score = int(data['best_score'])
            if 'best_sector' in data:
                best_badge._sector_id = int(data['best_sector'])
        
        if 'last_badge' in data:
            last_badge = badges[0]  # 已经按时间倒序排列
            last_badge._badge_name = data['last_badge']
        
        db.session.commit()
        return jsonify({"success": True, "message": "Badge information updated successfully"})
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR updating badge info: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/update_user/<string:uid>', methods=['PUT'])
def update_user(uid):
    # Authorization check
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403

    # Get the JSON data from the request
    data = request.get_json()
    print(f"Request Data: {data}")  # Log the incoming data

    # Find the user in the database
    user = User.query.filter_by(_uid=uid).first()
    if user:
        print(f"Found user: {user.uid}")  # Log the found user's UID
        
        # Update the user using the provided data
        user.update(data)  # Assuming `user.update(data)` is a method on your User model
        
        # Save changes to the database
        return jsonify({"message": "User updated successfully."}), 200
    else:
        print("User not found.")  # Log when user is not found
        return jsonify({"message": "User not found."}), 404



    
# Create an AppGroup for custom commands
custom_cli = AppGroup('custom', help='Custom commands')

# Define a command to run the data generation functions
@custom_cli.command('generate_data')
def generate_data():
    initUsers()
    initMicroblogs()
    initPersonas()
    initPersonaUsers()

# Register the custom command group with the Flask application
app.cli.add_command(custom_cli)
        
# this runs the flask application on the development server
if __name__ == "__main__":
    host = "0.0.0.0"
    port = app.config['FLASK_PORT']
    print(f"** Server running: http://localhost:{port}")  # Pretty link
    app.run(debug=True, host=host, port=port, use_reloader=False)
