# model/robop_user.py

from __init__ import app, db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from random import randint, choice

class RobopUser(db.Model):
    __tablename__ = "RobopUser"

    id = db.Column(db.Integer, primary_key=True)
    _uid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    _first_name = db.Column(db.String(60), nullable=False)
    _last_name = db.Column(db.String(60), nullable=False)
    _password = db.Column(db.String(255), nullable=False)

    _created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    _last_login = db.Column(db.DateTime, nullable=True)
    
    # APPENDED: Relationship to link badges to users
    badges = db.relationship("UserBadge", backref="user", lazy=True)

    def __init__(self, uid, first_name, last_name, password):
        self._uid = uid
        self._first_name = first_name
        self._last_name = last_name
        self._password = generate_password_hash(password)

    @property
    def uid(self):
        return self._uid
    
    @uid.setter
    def uid(self, value):
        self._uid = value
    
    @property
    def first_name(self):
        return self._first_name
    
    @first_name.setter
    def first_name(self, value):
        self._first_name = value
    
    @property
    def last_name(self):
        return self._last_name
    
    @last_name.setter
    def last_name(self, value):
        self._last_name = value


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
            "created": self._created.isoformat() if getattr(self, "_created", None) else None,
            "last_login": self._last_login.isoformat() if getattr(self, "_last_login", None) else None,
        }

    def touch_login(self):
        """Update last_login timestamp when a user successfully logs in."""
        self._last_login = datetime.now(timezone.utc)
        db.session.commit()


# --- APPENDED: NEW MODELS FOR BADGE FEATURE ---

class BadgeThreshold(db.Model):
    """Table to store achievement thresholds (The 'List' for CPT)"""
    __tablename__ = "BadgeThreshold"
    id = db.Column(db.Integer, primary_key=True)
    _name = db.Column(db.String(64), unique=True, nullable=False)
    _threshold = db.Column(db.Integer, nullable=False) 

    def __init__(self, name, threshold):
        self._name = name
        self._threshold = threshold

    def to_dict(self):
        return {"name": self._name, "threshold": self._threshold}

class UserBadge(db.Model):
    """Table to store badges earned by specific users"""
    __tablename__ = "UserBadge"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("RobopUser.id"), nullable=False)
    _sector_id = db.Column(db.Integer, nullable=False)
    _score = db.Column(db.Integer, nullable=False)
    _badge_name = db.Column(db.String(64), nullable=False)
    _date_earned = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, sector_id, score, badge_name):
        self.user_id = user_id
        self._sector_id = sector_id
        self._score = score
        self._badge_name = badge_name

    def to_dict(self):
        return {
            "sector": self._sector_id,
            "score": self._score,
            "badge": self._badge_name,
            "date": self._date_earned.isoformat()
        }


def initRobopUsers():
    """Create RobopUser table and (optionally) seed a demo user."""
    with app.app_context():
        # Create DB tables (includes RobopUser, BadgeThreshold, and UserBadge)
        db.create_all()

        # APPENDED: Seed Thresholds if table is empty
        if not BadgeThreshold.query.first():
            thresholds = [
                BadgeThreshold("Gold", 95),
                BadgeThreshold("Silver", 80),
                BadgeThreshold("Bronze", 65),
                BadgeThreshold("Participant", 0)
            ]
            for t in thresholds:
                db.session.add(t)
            db.session.commit()
            print("✅ Badge thresholds seeded.")

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
        
        # Seed test users
        test_users = [
            RobopUser(uid="alice", first_name="Alice", last_name="Test", password="pass"),
            RobopUser(uid="bob", first_name="Bob", last_name="Test", password="pass"),
            RobopUser(uid="charlie", first_name="Charlie", last_name="Test", password="pass"),
        ]

        for u in test_users:
            if not RobopUser.query.filter_by(_uid=u.uid).first():
                db.session.add(u)

        db.session.commit()

        # Seed badges for those same users
        if not UserBadge.query.first():
            thresholds = BadgeThreshold.query.all()

            for user in RobopUser.query.filter(
                RobopUser._uid.in_(["alice", "bob", "charlie"])
            ).all():

                for sector in range(1, 4):
                    score = randint(50, 100)
                    badge = max(
                        thresholds,
                        key=lambda t: score >= t._threshold
                    )._name

                    db.session.add(
                        UserBadge(
                            user_id=user.id,   # ← integer FK
                            sector_id=sector,
                            score=score,
                            badge_name=badge
                        )
                    )

            db.session.commit()
