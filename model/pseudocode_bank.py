# model/pseudocode_bank.py
from __init__ import app, db


class PseudocodeQuestionBank(db.Model):
    __tablename__ = "PseudocodeQuestionBank"

    id = db.Column(db.Integer, primary_key=True)

    level1 = db.Column(db.Text, nullable=True)
    level2 = db.Column(db.Text, nullable=True)
    level3 = db.Column(db.Text, nullable=True)
    level4 = db.Column(db.Text, nullable=True)
    level5 = db.Column(db.Text, nullable=True)

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


def initPseudocodeQuestionBank(force_recreate=False):
    """
    Call this ONCE during app startup.
    It creates the table and seeds 50 questions if empty.
    ✅ This version seeds 50 ROWS (IDs 1..50), 1 question per row.
    """
    with app.app_context():
        db.create_all()

        if force_recreate:
            print("Recreating PseudocodeQuestionBank...")
            PseudocodeQuestionBank.__table__.drop(db.engine, checkfirst=True)
            PseudocodeQuestionBank.__table__.create(db.engine, checkfirst=True)

        if PseudocodeQuestionBank.query.first():
            print("PseudocodeQuestionBank already seeded.")
            return

        # LEVEL 1 (Super Easy) 1–10
        level1_questions = [
            "Store the number 12 in x, then display x.",
            "Input a name and display 'Hi, ' plus the name.",
            "Set a ← 5 and b ← 7, then display a + b.",
            "Input n and display 'EVEN' if n is even, otherwise 'ODD'.",
            "Input temp and display 'Hot' if temp > 80, else 'Not hot'.",
            "Increase score by 1 and display it.",
            "Create list L ← [3, 6, 9] and display the first element.",
            "Display all numbers from 1 to 5.",
            "Input two numbers and display the larger one.",
            "Input age and display 'Adult' if age ≥ 18, else 'Minor'."
        ]

        # LEVEL 2 (Easy) 11–20
        level2_questions = [
            "Display the sum of numbers from 1 to 10.",
            "Given list A, count how many items are 0 and display the count.",
            "Input n and display 'Multiple of 3' if n is divisible by 3.",
            "Input 5 numbers and display their average.",
            "Given list L, display the last element.",
            "Input word and display 'YES' if it equals 'APCSP', else 'NO'.",
            "Given list L, display each element.",
            "Swap the values of x and y.",
            "Input n. Display 'Positive', 'Negative', or 'Zero'.",
            "Given list L, build list M containing only values greater than 10."
        ]

        # LEVEL 3 (Medium) 21–30
        level3_questions = [
            "Write IsPrime(n) that returns true if n is prime.",
            "Given list L, find and display the maximum value.",
            "Count vowels in string s and display the count.",
            "Reverse list L into new list R.",
            "Remove all 0s from list L while keeping order.",
            "Find the second-largest number in list L.",
            "Return true if string s is a palindrome.",
            "Roll a 6-sided die 100 times; count how many times 6 appears.",
            "Write CountMatches(L, target) that returns how many elements equal target.",
            "Given list L, display how many values are greater than the average."
        ]

        # LEVEL 4 (Hard) 31–40
        level4_questions = [
            "Find the mode of list L. If tie, return the smaller value.",
            "Merge two sorted lists A and B into sorted list C.",
            "Determine if two strings are anagrams.",
            "Remove duplicates from list L while keeping first occurrence.",
            "Write BinarySearch(L, target) for sorted list L.",
            "Rotate list L to the right by k steps.",
            "Find first pair in list L that adds to target.",
            "Find the longest word in list W.",
            "Run-length encode a string.",
            "Determine if list L is almost sorted with at most one swap."
        ]

        # LEVEL 5 (Hacker) 41–50
        level5_questions = [
            "Detect cycle in nextIndex list starting at index 1.",
            "Given grid of 0s and 1s, determine if path exists from (1,1) to (rows, cols).",
            "Write Caesar Encrypt(message, k).",
            "Write Caesar Decrypt(message, k).",
            "Return true if parentheses string is balanced.",
            "Display all primes up to n using sieve method.",
            "Return true if first player wins stone game (1 or 2 stones per turn).",
            "Combine transaction balances by name.",
            "Sort strings by length, then alphabetically.",
            "Find smallest missing positive integer in list L."
        ]

        # ✅ Seed 50 rows (IDs 1..50), one question per row
        for q in level1_questions:
            db.session.add(PseudocodeQuestionBank(level1=q))
        for q in level2_questions:
            db.session.add(PseudocodeQuestionBank(level2=q))
        for q in level3_questions:
            db.session.add(PseudocodeQuestionBank(level3=q))
        for q in level4_questions:
            db.session.add(PseudocodeQuestionBank(level4=q))
        for q in level5_questions:
            db.session.add(PseudocodeQuestionBank(level5=q))

        db.session.commit()
        print("PseudocodeQuestionBank seeded with 50 AP CSP questions.")