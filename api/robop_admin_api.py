import json
import os
import random
import string
from flask import Blueprint, jsonify, request, session
from model.robop_user import RobopUser, UserBadge, BadgeThreshold
from __init__ import db
from jinja2 import Template

robop_admin_api = Blueprint("robop_admin_api", __name__, url_prefix="/api/robop/admin")

# --- JINJA2 LOGIC (Captures ALL data currently in DB) ---
def run_jinja_backup():
    try:
        # These queries pull EVERY user and EVERY badge in the database
        users = RobopUser.query.all()
        badges = UserBadge.query.all()
        
        json_template = """
        {
            "users": [
                {% for user in users %}
                {
                    "uid": "{{ user.uid }}",
                    "first_name": "{{ user.first_name }}",
                    "last_name": "{{ user.last_name }}",
                    "password": "pass" 
                }{% if not loop.last %},{% endif %}
                {% endfor %}
            ],
            "badges": [
                {% for b in badges %}
                {
                    "user_uid": "{{ b.user.uid }}",
                    "sector_id": {{ b._sector_id }},
                    "badge_name": "{{ b._badge_name }}",
                    "score": {{ b._score }}
                }{% if not loop.last %},{% endif %}
                {% endfor %}
            ]
        }
        """
        template = Template(json_template)
        rendered_json = template.render(users=users, badges=badges)
        with open('robop_backup.json', 'w') as f:
            f.write(rendered_json)
        return True
    except Exception as e:
        print(f"Jinja Error: {e}")
        return False

# --- ROUTES ---

@robop_admin_api.route("/seed", methods=["POST"], strict_slashes=False)
def seed():
    try:
        # FIX: Removed the delete lines so original users are NOT destroyed
        
        if not BadgeThreshold.query.first():
            db.session.add(BadgeThreshold("Gold", 95))
            db.session.add(BadgeThreshold("Silver", 80))
            db.session.add(BadgeThreshold("Bronze", 65))
            db.session.commit()

        thresholds = BadgeThreshold.query.all()
        badge_pool = [t._name for t in thresholds]

        seeded_count = 0
        for i in range(50):
            char_pool = string.ascii_lowercase + string.digits
            uid = f"cadet_{''.join(random.choices(char_pool, k=5))}"
            
            # Selection: Only add if UID doesn't collide with existing users
            if not RobopUser.query.filter_by(_uid=uid).first():
                user = RobopUser(uid=uid, first_name="Mock", last_name=f"User_{i}", password="pass")
                db.session.add(user)
                db.session.flush() 

                if random.random() > 0.3:
                    badge = UserBadge(user_id=user.id, sector_id=random.randint(1, 5),
                                     score=random.randint(60, 100), badge_name=random.choice(badge_pool))
                    db.session.add(badge)
                seeded_count += 1

        db.session.commit()
        return jsonify({"success": True, "message": f"Added {seeded_count} cadets on top of existing users."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Python Error: {str(e)}"}), 500

@robop_admin_api.route("/backup_data", methods=["POST"], strict_slashes=False)
def backup():
    # This now captures everyone (Originals + Mock)
    if run_jinja_backup():
        return jsonify({"success": True, "message": "Jinja2 Snapshot includes ALL users."}), 200
    return jsonify({"success": False, "message": "Jinja2 Generation Failed."}), 500

@robop_admin_api.route("/clear", methods=["POST"], strict_slashes=False)
def clear():
    """Wipes everything for destruction demo."""
    try:
        UserBadge.query.delete()
        RobopUser.query.delete()
        db.session.commit()
        return jsonify({"success": True, "message": "All data purged."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@robop_admin_api.route("/restore", methods=["POST"], strict_slashes=False)
def restore():
    """Restores everyone from the JSON."""
    try:
        if not os.path.exists('robop_backup.json'):
            return jsonify({"success": False, "message": "No JSON Backup found."}), 404
        
        with open('robop_backup.json', 'r') as f:
            data = json.load(f)
        
        user_map = {}
        for u in data['users']:
            # Selection logic to prevent crashing on existing users
            existing = RobopUser.query.filter_by(_uid=u['uid']).first()
            if not existing:
                new_user = RobopUser(uid=u['uid'], first_name=u['first_name'], last_name=u['last_name'], password=u['password'])
                db.session.add(new_user)
                db.session.flush() 
                user_map[u['uid']] = new_user.id
            else:
                user_map[u['uid']] = existing.id
        
        for b in data['badges']:
            target_id = user_map.get(b['user_uid'])
            if target_id:
                # Avoid duplicate badges for the same sector
                if not UserBadge.query.filter_by(user_id=target_id, _sector_id=b['sector_id']).first():
                    new_badge = UserBadge(user_id=target_id, sector_id=b['sector_id'], score=b['score'], badge_name=b['badge_name'])
                    db.session.add(new_badge)
        
        db.session.commit()
        return jsonify({"success": True, "message": "Database successfully restored from JSON."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500