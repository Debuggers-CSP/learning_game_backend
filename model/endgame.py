from datetime import datetime, timezone

from __init__ import app, db


class Player(db.Model):
    __tablename__ = "Players"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    final_attempts = db.Column(db.Integer, nullable=True)
    final_badge_id = db.Column(db.Integer, db.ForeignKey("Badges.id"), nullable=True)
    final_answer = db.Column(db.Text, nullable=True)
    final_correct = db.Column(db.Boolean, nullable=True)

    badges = db.relationship("PlayerBadge", backref="player", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "final_attempts": self.final_attempts,
            "final_badge_id": self.final_badge_id,
            "final_correct": self.final_correct,
        }


class Badge(db.Model):
    __tablename__ = "Badges"

    id = db.Column(db.Integer, primary_key=True)
    badge_name = db.Column(db.String(80), unique=True, nullable=False)

    player_badges = db.relationship("PlayerBadge", backref="badge", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "badge_name": self.badge_name
        }


class PlayerBadge(db.Model):
    __tablename__ = "PlayerBadges"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("Players.id"), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey("Badges.id"), nullable=False)
    attempts = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "player_id": self.player_id,
            "badge_id": self.badge_id,
            "badge_name": self.badge.badge_name if self.badge else None,
            "attempts": self.attempts,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


def _seed_badges():
    default_badges = [
        "Explorer",
        "Solver",
        "Optimizer",
        "Debugger",
        "Champion",
    ]

    if not Badge.query.first():
        for name in default_badges:
            db.session.add(Badge(badge_name=name))
        db.session.commit()


def init_endgame_data():
    with app.app_context():
        db.create_all()
        _seed_badges()
