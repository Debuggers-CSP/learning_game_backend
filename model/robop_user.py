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
    
    # Relationship to link badges to users
    badges = db.relationship("UserBadge", backref="user", lazy=True)
    progress = db.relationship("Progress", backref="user", uselist=False, lazy=True)

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
            "github": getattr(self, "github", None),
            "created": self._created.isoformat() if self._created else None
        }

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


# --- UPDATED MODELS FOR BADGE FEATURE ---

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
    """Table to store badges earned by specific users with CPT metrics"""
    __tablename__ = "UserBadge"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("RobopUser.id"), nullable=False)
    _sector_id = db.Column(db.Integer, nullable=False)
    _module_id = db.Column(db.Integer, nullable=False) # Robot=0, Pseudo=1, MCQ=2
    _attempts = db.Column(db.Integer, nullable=False)
    _used_autofill = db.Column(db.Boolean, nullable=False, default=False)
    _badge_name = db.Column(db.String(64), nullable=False)
    _date_earned = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, sector_id, module_id, attempts, used_autofill, badge_name):
        self.user_id = user_id
        self._sector_id = sector_id
        self._module_id = module_id
        self._attempts = attempts
        self._used_autofill = used_autofill
        self._badge_name = badge_name

    def to_dict(self):
        return {
            "sector": self._sector_id,
            "module": self._module_id,
            "attempts": self._attempts,
            "autofill": self._used_autofill,
            "badge": self._badge_name,
            "date": self._date_earned.isoformat()
        }


class StationHint(db.Model):
    """Satisfies the 'List' requirement for the Create PT"""
    __tablename__ = "StationHint"
    id = db.Column(db.Integer, primary_key=True)
    module_key = db.Column(db.String(64), unique=True, nullable=False)  # e.g. "s1_m0"
    hint_collection = db.Column(db.JSON, nullable=False)  # Stores the list of AI hints

    def __init__(self, key, hints):
        self.module_key = key
        self.hint_collection = hints
class Progress(db.Model):  # START ADDING HERE
    """Tracks user's game/level progress"""
    __tablename__ = "Progress"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("RobopUser.id"), nullable=False, unique=True)
    
    _current_sector = db.Column(db.Integer, default=1, nullable=False)
    _current_module = db.Column(db.Integer, default=0, nullable=False)
    _total_score = db.Column(db.Integer, default=0, nullable=False)
    _completed_modules = db.Column(db.JSON, default=list, nullable=False)
    _last_played = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __init__(self, user_id):
        self.user_id = user_id
        self._current_sector = 1
        self._current_module = 0
        self._total_score = 0
        self._completed_modules = []
    
    def complete_module(self, sector_id, module_id, score=0):
        """Mark a module as completed"""
        module_key = f"s{sector_id}_m{module_id}"
        
        if self._completed_modules is None:
            self._completed_modules = []
        
        if module_key not in self._completed_modules:
            self._completed_modules.append(module_key)
        
        self._total_score += score
        self._last_played = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        return {
            "current_sector": self._current_sector,
            "current_module": self._current_module,
            "total_score": self._total_score,
            "completed_modules": self._completed_modules if self._completed_modules else []
        }

def initRobopUsers():
    """Create RobopUser table and (optionally) seed a demo user."""
    with app.app_context():
        # Create DB tables
        db.create_all()

        # Seed Thresholds if table is empty
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
                password=app.config.get("DEFAULT_PASSWORD", "password123")
            )
            demo.create()
            print("✅ RobopUser table ready + seeded demo user.")
        except IntegrityError:
            db.session.rollback()
            print("✅ RobopUser table ready (demo user already exists).")
        
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

        # Seed badges for those same users with new model structure
        if not UserBadge.query.first():
            for user in RobopUser.query.filter(RobopUser._uid.in_(["alice", "bob", "charlie"])).all():
                for sector in range(1, 4):
                    db.session.add(
                        UserBadge(
                            user_id=user.id,
                            sector_id=sector,
                            module_id=randint(0,2),
                            attempts=randint(1,5),
                            used_autofill=choice([True, False]),
                            badge_name="Seed Badge"
                        )
                    )
            db.session.commit()
            print("✅ Seed badges updated to new model.")
         # Create progress for all users
        for user in RobopUser.query.all():
            if not Progress.query.filter_by(user_id=user.id).first():
                progress = Progress(user_id=user.id)
                db.session.add(progress)
        db.session.commit()
        print("✅ Progress created for all users.")