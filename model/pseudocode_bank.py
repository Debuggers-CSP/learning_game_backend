# model/pseudocode_bank.py

from __init__ import app, db


class PseudocodeQuestionBank(db.Model):
    """
    One table:
      - each column is a level (1..5)
      - each row is a slot (10 rows)
      - each cell is a question string
    """
    __tablename__ = "PseudocodeQuestionBank"

    id = db.Column(db.Integer, primary_key=True)

    # NEW schema: 5 levels
    level1 = db.Column(db.Text, nullable=True)  # Super Easy
    level2 = db.Column(db.Text, nullable=True)  # Easy
    level3 = db.Column(db.Text, nullable=True)  # Medium
    level4 = db.Column(db.Text, nullable=True)  # Hard
    level5 = db.Column(db.Text, nullable=True)  # Hacker

    def __init__(self, level1=None, level2=None, level3=None, level4=None, level5=None):
        self.level1 = level1
        self.level2 = level2
        self.level3 = level3
        self.level4 = level4
        self.level5 = level5

    def to_dict(self):
        return {
            "id": self.id,
            "level1": self.level1,
            "level2": self.level2,
            "level3": self.level3,
            "level4": self.level4,
            "level5": self.level5,
        }


def _table_exists_and_has_column(table_name: str, col_name: str) -> bool:
    """
    SQLite-safe check:
    - if table doesn't exist -> PRAGMA returns empty -> False
    - if table exists but missing column -> False
    - if table exists and has column -> True
    """
    try:
        rows = db.session.execute(db.text(f'PRAGMA table_info("{table_name}")')).fetchall()
        if not rows:
            return False
        return any(r[1] == col_name for r in rows)  # r[1] is column name
    except Exception:
        return False


def initPseudocodeQuestionBank(force_recreate: bool = False):
    """
    Creates/seeds the pseudocode table.
    If it detects the OLD schema (super_easy/easy/medium),
    it will DROP and recreate ONLY this table (not the whole DB).
    """
    with app.app_context():
        # Ensure tables exist (won't alter existing schema)
        db.create_all()

        # If caller forces recreate, do it
        if force_recreate:
            print("⚠️ force_recreate=True: Dropping & recreating PseudocodeQuestionBank only...")
            PseudocodeQuestionBank.__table__.drop(db.engine, checkfirst=True)
            PseudocodeQuestionBank.__table__.create(db.engine, checkfirst=True)

        # Auto-migrate: if new column doesn't exist, old schema is present
        if not _table_exists_and_has_column("PseudocodeQuestionBank", "level1"):
            print("⚠️ Old PseudocodeQuestionBank schema detected. Dropping & recreating this table only...")
            PseudocodeQuestionBank.__table__.drop(db.engine, checkfirst=True)
            PseudocodeQuestionBank.__table__.create(db.engine, checkfirst=True)

        # If already seeded (any row exists), stop
        if PseudocodeQuestionBank.query.first():
            print("✅ PseudocodeQuestionBank ready (already has data).")
            return

        # ----------------------------
        # NEW QUESTIONS (50 total)
        # ----------------------------

        level1_questions = [
            "Store the number 12 in x, then display x.",
            "Input a name and display \"Hi, \" plus the name.",
            "Set a ← 5 and b ← 7, then display a + b.",
            "Input n and display \"EVEN\" if n is even, otherwise \"ODD\".",
            "Input temp and display \"Hot\" if temp > 80, else \"Not hot\".",
            "Increase score by 1 and display it. (Assume score already exists.)",
            "Create list L ← [3, 6, 9] and display the first element.",
            "Display all numbers from 1 to 5.",
            "Input two numbers and display the larger one.",
            "Input age and display \"Adult\" if age ≥ 18, else \"Minor\"."
        ]

        level2_questions = [
            "Display the sum of numbers from 1 to 10.",
            "Given list A, count how many items are 0 and display the count.",
            "Input n and display \"Multiple of 3\" if n is divisible by 3.",
            "Input 5 numbers (one at a time) and display their average.",
            "Given list L, display the last element of L.",
            "Input word and display \"YES\" if it equals \"APCSP\", else \"NO\".",
            "Given list L, display each element.",
            "Swap the values of x and y.",
            "Input n. Display \"Positive\", \"Negative\", or \"Zero\".",
            "Given list L, build list M containing only values greater than 10."
        ]

        level3_questions = [
            "Write IsPrime(n) that returns true if n is prime, else false.",
            "Given list L, find and display the maximum value.",
            "Count vowels in a string s and display the count.",
            "Reverse list L into a new list R (do not modify L).",
            "Remove all 0s from list L while keeping order; store result in NEW.",
            "Find the second-largest number in list L (assume all values are distinct).",
            "Return true if string s is a palindrome, else false.",
            "Roll a 6-sided die 100 times; count how many times the roll is 6; display count.",
            "Write CountMatches(L, target) that returns how many elements equal target.",
            "Given list L, display how many values are greater than the average of the list."
        ]

        level4_questions = [
            "Find the mode (most frequent value) of list L. If tie, return smaller value.",
            "Merge two sorted lists A and B into one sorted list C.",
            "Determine if two strings s1 and s2 are anagrams (same letters with same counts).",
            "Remove duplicates from list L while keeping the first occurrence order.",
            "Write BinarySearch(L, target) for sorted list L. Return index if found, else -1.",
            "Rotate list L to the right by k steps (wrap around). Store in R.",
            "Find the first pair of numbers in list L that adds to target. Return the pair, else [-1, -1].",
            "Find the longest word in list W. If tie, choose the earliest one.",
            "Run-length encode a string s (example: \"aaabb\" → \"a3b2\").",
            "Determine if list L is almost sorted (sortable by swapping at most one pair)."
        ]

        level5_questions = [
            "You have list nextIndex; starting at index 1, detect if there is a cycle. Return true/false.",
            "Given a grid of 0s and 1s, find if there is a path from (1,1) to (rows, cols). Return true/false.",
            "Caesar Cipher: Write Encrypt(message, k) shifting letters forward by k with wrap-around.",
            "Caesar Cipher: Write Decrypt(message, k) that reverses the shift.",
            "Balanced parentheses: Given string s containing only ( and ), return true if balanced.",
            "Sieve-style primes: Display all primes up to n using a mark-multiples approach.",
            "Game winner: n stones, players take 1 or 2; return true if first player can force win.",
            "Given transactions (name, amount) in list T, output each name’s total balance.",
            "Sort strings by length; if tie, sort alphabetically. Store sorted list in S.",
            "Find the smallest missing positive integer in list L."
        ]

        # 10 rows, each row has 5 questions (one per level)
        for i in range(10):
            db.session.add(PseudocodeQuestionBank(
                level1=level1_questions[i],
                level2=level2_questions[i],
                level3=level3_questions[i],
                level4=level4_questions[i],
                level5=level5_questions[i],
            ))

        db.session.commit()
        print("✅ PseudocodeQuestionBank table created + seeded (5 levels, 50 questions).")
