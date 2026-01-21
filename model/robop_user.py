# model/robop_user.py

from __init__ import app, db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError


class RobopUser(db.Model):
    __tablename__ = "RobopUser"

    id = db.Column(db.Integer, primary_key=True)
    _uid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    _first_name = db.Column(db.String(60), nullable=False)
    _last_name = db.Column(db.String(60), nullable=False)
    _password = db.Column(db.String(255), nullable=False)

    _created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    _last_login = db.Column(db.DateTime, nullable=True)

    def __init__(self, uid, first_name, last_name, password):
        self._uid = uid
        self._first_name = first_name
        self._last_name = last_name
        self._password = generate_password_hash(password)

    @property
    def uid(self):
        return self._uid

    @property
    def first_name(self):
        return self._first_name

    @property
    def last_name(self):
        return self._last_name

    def is_password(self, password):
        return check_password_hash(self._password, password)

    def create(self):
        db.session.add(self)
        db.session.commit()
        return self

    def read(self):
        return {
            "id": self.id,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "github": self.github,
            # do NOT return raw password
            "created": self.created.isoformat() if self.created else None
        }

    # Keep compatibility with APIs that expect to_dict()
    def to_dict(self):
        """Return a JSON-safe representation of this user."""
        return {
            "id": self.id,
            "github": getattr(self, "github", None),
            "first_name": getattr(self, "first_name", None),
            "last_name": getattr(self, "last_name", None),
            "role": getattr(self, "role", None),
            "created": self.created.isoformat() if getattr(self, "created", None) else None,
            "last_login": self.last_login.isoformat() if getattr(self, "last_login", None) else None,
        }

    def touch_login(self):
        """Update last_login timestamp when a user successfully logs in."""
        self.last_login = datetime.now(timezone.utc)
        db.session.commit()


def initRobopUsers():
    """Create RobopUser table and (optionally) seed a demo user."""
    with app.app_context():
        # Create DB tables (includes RobopUser)
        db.create_all()

        # Optional seed user
        try:
            demo = RobopUser(
                uid="demo_robop",
                first_name="Demo",
                last_name="Robop",
                password=app.config["DEFAULT_PASSWORD"]
            )
            demo.create()
            print("✅ RobopUser table ready + seeded demo user.")
        except IntegrityError:
            db.session.rollback()
            print("✅ RobopUser table ready (demo user already exists).")
        except Exception as e:
            db.session.rollback()
            print(f"⚠️ RobopUser init error: {e}")
