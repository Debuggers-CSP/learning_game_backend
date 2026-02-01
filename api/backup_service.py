from jinja2 import Template
import os
from model.robop_user import RobopUser, UserBadge

def generate_jinja_backup():
    """Uses Jinja2 to create a JSON file that can be used for full recovery."""
    try:
        users = RobopUser.query.all()
        badges = UserBadge.query.all()

        # Updated Template: Contains raw fields needed to recreate DB objects
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
        print(f"Jinja2 Error: {e}")
        return False