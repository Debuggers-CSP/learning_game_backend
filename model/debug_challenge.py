from datetime import datetime
import json

from __init__ import app, db


class DebugChallenge(db.Model):
    __tablename__ = "DebugChallenges"

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(32), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    buggy_code = db.Column(db.Text, nullable=False)
    expected_behavior = db.Column(db.Text, nullable=True)
    expected_output = db.Column(db.Text, nullable=True)
    test_harness = db.Column(db.Text, nullable=True)
    solution_keywords = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "level": self.level,
            "title": self.title,
            "prompt": self.prompt,
            "buggy_code": self.buggy_code,
            "expected_behavior": self.expected_behavior,
        }


class DebugBadge(db.Model):
    __tablename__ = "DebugBadges"

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(32), unique=True, nullable=False)
    badge_name = db.Column(db.String(80), unique=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "level": self.level,
            "badge_name": self.badge_name,
        }


class DebugBadgeEarned(db.Model):
    __tablename__ = "DebugBadgeEarned"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("Players.id"), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey("DebugBadges.id"), nullable=False)
    attempts = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    badge = db.relationship("DebugBadge", backref="earned", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "player_id": self.player_id,
            "badge_id": self.badge_id,
            "badge_name": self.badge.badge_name if self.badge else None,
            "level": self.badge.level if self.badge else None,
            "attempts": self.attempts,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class DebugHintUsage(db.Model):
    __tablename__ = "DebugHintUsage"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("Players.id"), nullable=False)
    level = db.Column(db.String(32), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("DebugChallenges.id"), nullable=False)
    hints_used = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "player_id": self.player_id,
            "level": self.level,
            "challenge_id": self.challenge_id,
            "hints_used": self.hints_used,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def _seed_debug_badges():
    badges = [
        ("beginner", "Debug Beginner"),
        ("intermediate", "Debug Intermediate"),
        ("hard", "Debug Hard"),
    ]

    if not DebugBadge.query.first():
        for level, name in badges:
            db.session.add(DebugBadge(level=level, badge_name=name))
        db.session.commit()


def _seed_debug_challenges():
    existing = DebugChallenge.query.first()
    if existing:
        sample = (existing.prompt or "") + " " + (existing.expected_behavior or "")
        needs_reseed = "explain" in sample.lower()
        if not needs_reseed:
            return
        DebugChallenge.__table__.drop(db.engine, checkfirst=True)
        DebugChallenge.__table__.create(db.engine, checkfirst=True)

    beginner = [
        {
            "title": "Missing Colon",
            "prompt": "Fix the bug so the program prints 'Adult' if age ≥ 18, otherwise 'Minor'.",
            "buggy_code": "age = 16\nif age >= 18\n    print(\"Adult\")\nelse:\n    print(\"Minor\")",
            "expected_behavior": "Submit corrected Python code only. Output should be 'Minor' for age 16 and 'Adult' for age 18.",
            "expected_output": "Minor",
            "solution_keywords": ["if", "else", "print"],
        },
        {
            "title": "Equality Check",
            "prompt": "Fix the bug so the program prints 'Win' when score equals 10.",
            "buggy_code": "score = 10\nif score = 10:\n    print(\"Win\")",
            "expected_behavior": "Submit corrected Python code only. Output should be 'Win' when score is 10.",
            "expected_output": "Win",
            "solution_keywords": ["if", "print"],
        },
        {
            "title": "String Join",
            "prompt": "Fix the bug so the program prints 'Hi, Ana'.",
            "buggy_code": "name = \"Ana\"\nprint(\"Hi, \" + Name)",
            "expected_behavior": "Submit corrected Python code only. Output should be 'Hi, Ana'.",
            "expected_output": "Hi, Ana",
            "solution_keywords": ["print"],
        },
        {
            "title": "Indentation",
            "prompt": "Fix the bug so the program prints numbers 1 to 3.",
            "buggy_code": "for i in range(1, 4):\nprint(i)",
            "expected_behavior": "Submit corrected Python code only. Output should be 1, 2, 3 on separate lines.",
            "expected_output": "1\n2\n3",
            "solution_keywords": ["for", "range", "print"],
        },
        {
            "title": "Variable Name",
            "prompt": "Fix the bug so the program displays the total.",
            "buggy_code": "total = 7 + 5\nprint(totl)",
            "expected_behavior": "Submit corrected Python code only. Output should be 12.",
            "expected_output": "12",
            "solution_keywords": ["print"],
        },
        {
            "title": "List Index",
            "prompt": "Fix the bug so the program prints the first item in the list.",
            "buggy_code": "items = [\"apple\", \"banana\"]\nprint(items[1])",
            "expected_behavior": "Submit corrected Python code only. Output should be 'apple'.",
            "expected_output": "apple",
            "solution_keywords": ["print"],
        },
    ]

    intermediate = [
        {
            "title": "Count Evens",
            "prompt": "Fix the bug so the program counts even numbers and prints the count.",
            "buggy_code": "nums = [2, 3, 4, 5]\ncount = 0\nfor n in nums:\n    if n % 2 = 0:\n        count += 1\nprint(count)",
            "expected_behavior": "Submit corrected Python code only. Output should be 2.",
            "expected_output": "2",
            "solution_keywords": ["for", "if", "print"],
        },
        {
            "title": "Sum List",
            "prompt": "Fix the bug so the program sums all numbers in the list.",
            "buggy_code": "nums = [1, 2, 3]\nTotal = 0\nfor i in range(len(nums)):\n    total += nums[i]\nprint(total)",
            "expected_behavior": "Submit corrected Python code only. Output should be 6.",
            "expected_output": "6",
            "solution_keywords": ["for", "range", "print"],
        },
        {
            "title": "Find Max",
            "prompt": "Fix the bug so the program prints the largest number in the list.",
            "buggy_code": "nums = [3, 9, 4]\nmax_num = 0\nfor n in nums:\n    if n < max_num:\n        max_num = n\nprint(max_num)",
            "expected_behavior": "Submit corrected Python code only. Output should be 9.",
            "expected_output": "9",
            "solution_keywords": ["for", "if", "print"],
        },
        {
            "title": "Average",
            "prompt": "Fix the bug so the program prints the average of the list.",
            "buggy_code": "nums = [4, 6, 8]\ntotal = 0\nfor n in nums:\n    total += n\naverage = total / 2\nprint(average)",
            "expected_behavior": "Submit corrected Python code only. Output should be 6.",
            "expected_output": "6|6.0",
            "solution_keywords": ["for", "print"],
        },
        {
            "title": "Filter Positives",
            "prompt": "Fix the bug so the program builds a list of only positive numbers.",
            "buggy_code": "nums = [-1, 2, -3, 4]\npositives = []\nfor n in nums:\n    if n > 0:\n        positives.append = n\nprint(positives)",
            "expected_behavior": "Submit corrected Python code only. Output should be [2, 4].",
            "expected_output": "[2, 4]",
            "solution_keywords": ["for", "if", "append", "print"],
        },
        {
            "title": "Loop Bounds",
            "prompt": "Fix the bug so the program prints numbers 0 to 4.",
            "buggy_code": "for i in range(1, 5):\n    print(i)",
            "expected_behavior": "Submit corrected Python code only. Output should be 0,1,2,3,4.",
            "expected_output": "0\n1\n2\n3\n4",
            "solution_keywords": ["for", "range", "print"],
        },
    ]

    hard = [
        {
            "title": "Inventory Tally",
            "prompt": "Fix the bug so the program sums quantities by item name and prints totals.",
            "buggy_code": "items = [(\"pen\", 2), (\"pen\", 3), (\"book\", 1)]\ncounts = {}\nfor name, qty in items:\n    counts[name] = qty\nprint(counts)",
            "expected_behavior": "Submit corrected Python code only. Output should be {'pen': 5, 'book': 1}.",
            "expected_output": "{'pen': 5, 'book': 1}|{'book': 1, 'pen': 5}",
            "solution_keywords": ["for", "print", "counts"],
        },
        {
            "title": "Safe Divide",
            "prompt": "Fix the bug so safe_divide returns 0 when divisor is 0, else returns the division.",
            "buggy_code": "def safe_divide(a, b):\n    if b == 0:\n        return a / b\n    return 0",
            "expected_behavior": "Submit corrected Python code only. safe_divide(10, 0) returns 0; safe_divide(10, 2) returns 5.",
            "expected_output": "0\n5",
            "test_harness": "print(safe_divide(10, 0))\nprint(safe_divide(10, 2))",
            "solution_keywords": ["if", "return"],
        },
        {
            "title": "Order Status",
            "prompt": "Fix the bug so orders with total ≥ 50 are labeled 'free shipping'.",
            "buggy_code": "orders = [25, 50, 75]\nlabels = []\nfor total in orders:\n    if total > 50:\n        labels.append(\"free shipping\")\n    else:\n        labels.append(\"standard\")\nprint(labels)",
            "expected_behavior": "Submit corrected Python code only. Output should be ['standard', 'free shipping', 'free shipping'].",
            "expected_output": "['standard', 'free shipping', 'free shipping']",
            "solution_keywords": ["for", "if", "else", "append", "print"],
        },
        {
            "title": "Stop on Error",
            "prompt": "Fix the bug so the loop stops when it hits 'ERROR'.",
            "buggy_code": "events = [\"OK\", \"ERROR\", \"OK\"]\nfor e in events:\n    if e == \"ERROR\":\n        continue\n    print(e)",
            "expected_behavior": "Submit corrected Python code only. Output should be only 'OK' once and stop at ERROR.",
            "expected_output": "OK",
            "solution_keywords": ["for", "if", "break"],
        },
        {
            "title": "Running Total",
            "prompt": "Fix the bug so the program outputs the running total list.",
            "buggy_code": "nums = [1, 2, 3]\nresult = []\nfor n in nums:\n    total = 0\n    total += n\n    result.append(total)\nprint(result)",
            "expected_behavior": "Submit corrected Python code only. Output should be [1, 3, 6].",
            "expected_output": "[1, 3, 6]",
            "solution_keywords": ["for", "append", "print"],
        },
        {
            "title": "Email Checker",
            "prompt": "Fix the bug so the program prints 'valid' only when the string contains '@' and '.'.",
            "buggy_code": "email = \"student@example.com\"\nif \"@\" in email or \".\" in email:\n    print(\"valid\")\nelse:\n    print(\"invalid\")",
            "expected_behavior": "Submit corrected Python code only. Output should be 'valid' only when both symbols are present.",
            "expected_output": "valid",
            "solution_keywords": ["if", "else", "print"],
        },
    ]

    for level, rows in [
        ("beginner", beginner),
        ("intermediate", intermediate),
        ("hard", hard),
    ]:
        for row in rows:
            db.session.add(DebugChallenge(
                level=level,
                title=row["title"],
                prompt=row["prompt"],
                buggy_code=row["buggy_code"],
                expected_behavior=row.get("expected_behavior"),
                expected_output=row.get("expected_output"),
                test_harness=row.get("test_harness"),
                solution_keywords=json.dumps(row.get("solution_keywords", []))
            ))

    db.session.commit()


def init_debug_challenge_data():
    with app.app_context():
        db.create_all()
        _seed_debug_badges()
        _seed_debug_challenges()
