# model/pseudocodeanswer_bank.py
from __init__ import app, db


class PseudocodeAnswerBank(db.Model):
    __tablename__ = "PseudocodeAnswerBank"

    id = db.Column(db.Integer, primary_key=True)

    # Links to PseudocodeQuestionBank.id (1..50)
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("PseudocodeQuestionBank.id"),
        nullable=False,
        index=True,
        unique=True
    )

    # optional: "level1".."level5"
    level = db.Column(db.String(16), nullable=True)

    # canonical answer text
    answer = db.Column(db.Text, nullable=False)

    def __init__(self, question_id: int, answer: str, level: str = None):
        self.question_id = question_id
        self.answer = answer
        self.level = level

    def to_dict(self):
        return {
            "id": self.id,
            "question_id": self.question_id,
            "level": self.level,
            "answer": self.answer
        }


def initPseudocodeAnswerBank(force_recreate: bool = False):
    """
    Call once at app startup.
    Creates table and seeds answers if empty.
    """
    from model.pseudocode_bank import PseudocodeQuestionBank  # avoid circular import

    with app.app_context():
        db.create_all()

        if force_recreate:
            print("Recreating PseudocodeAnswerBank...")
            PseudocodeAnswerBank.__table__.drop(db.engine, checkfirst=True)
            PseudocodeAnswerBank.__table__.create(db.engine, checkfirst=True)

        if PseudocodeAnswerBank.query.first():
            print("PseudocodeAnswerBank already seeded.")
            return

        # ✅ Canonical Answer Key (1..50)
        # Matches your worksheet pseudocode style
        ANSWERS = {
            # LEVEL 1
            1: "x ← 12\nDISPLAY x",
            2: 'INPUT name\nDISPLAY "Hi, " + name',
            3: "a ← 5\nb ← 7\nDISPLAY a + b",
            4: 'INPUT n\nIF n MOD 2 = 0\n  DISPLAY "EVEN"\nELSE\n  DISPLAY "ODD"\nEND IF',
            5: 'INPUT temp\nIF temp > 80\n  DISPLAY "Hot"\nELSE\n  DISPLAY "Not hot"\nEND IF',
            6: "score ← score + 1\nDISPLAY score",
            7: "L ← [3, 6, 9]\nDISPLAY L[1]",
            8: "FOR i ← 1 TO 5\n  DISPLAY i\nEND FOR",
            9: "INPUT a\nINPUT b\nIF a > b\n  DISPLAY a\nELSE\n  DISPLAY b\nEND IF",
            10: 'INPUT age\nIF age ≥ 18\n  DISPLAY "Adult"\nELSE\n  DISPLAY "Minor"\nEND IF',

            # LEVEL 2
            11: "sum ← 0\nFOR i ← 1 TO 10\n  sum ← sum + i\nEND FOR\nDISPLAY sum",
            12: "count ← 0\nFOR EACH item IN A\n  IF item = 0\n    count ← count + 1\n  END IF\nEND FOR\nDISPLAY count",
            13: 'INPUT n\nIF n MOD 3 = 0\n  DISPLAY "Multiple of 3"\nEND IF',
            14: "sum ← 0\nFOR i ← 1 TO 5\n  INPUT n\n  sum ← sum + n\nEND FOR\nDISPLAY sum / 5",
            15: "DISPLAY L[LENGTH(L)]",
            16: 'INPUT word\nIF word = "APCSP"\n  DISPLAY "YES"\nELSE\n  DISPLAY "NO"\nEND IF',
            17: "FOR EACH item IN L\n  DISPLAY item\nEND FOR",
            18: "temp ← x\nx ← y\ny ← temp",
            19: 'INPUT n\nIF n > 0\n  DISPLAY "Positive"\nELSE IF n < 0\n  DISPLAY "Negative"\nELSE\n  DISPLAY "Zero"\nEND IF',
            20: "M ← []\nFOR EACH item IN L\n  IF item > 10\n    APPEND(M, item)\n  END IF\nEND FOR",

            # LEVEL 3
            21: "PROCEDURE IsPrime(n)\n  IF n ≤ 1\n    RETURN false\n  END IF\n  FOR i ← 2 TO n − 1\n    IF n MOD i = 0\n      RETURN false\n    END IF\n  END FOR\n  RETURN true\nEND PROCEDURE",
            22: "max ← L[1]\nFOR EACH item IN L\n  IF item > max\n    max ← item\n  END IF\nEND FOR\nDISPLAY max",
            23: 'count ← 0\nFOR EACH char IN s\n  IF LOWER(char) IN ["a","e","i","o","u"]\n    count ← count + 1\n  END IF\nEND FOR\nDISPLAY count',
            24: "R ← []\nFOR i ← LENGTH(L) TO 1\n  APPEND(R, L[i])\nEND FOR",
            25: "NEW ← []\nFOR EACH item IN L\n  IF item ≠ 0\n    APPEND(NEW, item)\n  END IF\nEND FOR",
            26: "SORT(L)\nDISPLAY L[LENGTH(L) − 1]",
            27: "IF s = REVERSE(s)\n  RETURN true\nELSE\n  RETURN false\nEND IF",
            28: "count ← 0\nREPEAT 100 TIMES\n  roll ← RANDOM(1,6)\n  IF roll = 6\n    count ← count + 1\n  END IF\nEND REPEAT\nDISPLAY count",
            29: "PROCEDURE CountMatches(L, target)\n  count ← 0\n  FOR EACH item IN L\n    IF item = target\n      count ← count + 1\n    END IF\n  END FOR\n  RETURN count\nEND PROCEDURE",
            30: "sum ← 0\nFOR EACH item IN L\n  sum ← sum + item\nEND FOR\navg ← sum / LENGTH(L)\n\ncount ← 0\nFOR EACH item IN L\n  IF item > avg\n    count ← count + 1\n  END IF\nEND FOR\nDISPLAY count",

            # LEVEL 4
            31: "bestValue ← L[1]\nbestCount ← 0\n\nFOR EACH v IN L\n  c ← 0\n  FOR EACH x IN L\n    IF x = v\n      c ← c + 1\n    END IF\n  END FOR\n\n  IF c > bestCount\n    bestCount ← c\n    bestValue ← v\n  ELSE IF c = bestCount AND v < bestValue\n    bestValue ← v\n  END IF\nEND FOR\n\nDISPLAY bestValue",
            32: "i ← 1\nj ← 1\nC ← []\n\nWHILE i ≤ LENGTH(A) AND j ≤ LENGTH(B)\n  IF A[i] ≤ B[j]\n    APPEND(C, A[i])\n    i ← i + 1\n  ELSE\n    APPEND(C, B[j])\n    j ← j + 1\n  END IF\nEND WHILE\n\nWHILE i ≤ LENGTH(A)\n  APPEND(C, A[i])\n  i ← i + 1\nEND WHILE\n\nWHILE j ≤ LENGTH(B)\n  APPEND(C, B[j])\n  j ← j + 1\nEND WHILE",
            33: "IF LENGTH(s1) ≠ LENGTH(s2)\n  RETURN false\nEND IF\n\nFOR EACH ch IN s1\n  count1 ← 0\n  count2 ← 0\n\n  FOR EACH x IN s1\n    IF x = ch\n      count1 ← count1 + 1\n    END IF\n  END FOR\n\n  FOR EACH y IN s2\n    IF y = ch\n      count2 ← count2 + 1\n    END IF\n  END FOR\n\n  IF count1 ≠ count2\n    RETURN false\n  END IF\nEND FOR\n\nRETURN true",
            34: "R ← []\nFOR EACH item IN L\n  found ← false\n  FOR EACH x IN R\n    IF x = item\n      found ← true\n    END IF\n  END FOR\n  IF found = false\n    APPEND(R, item)\n  END IF\nEND FOR",
            35: "PROCEDURE BinarySearch(L, target)\n  low ← 1\n  high ← LENGTH(L)\n\n  WHILE low ≤ high\n    mid ← FLOOR((low + high) / 2)\n\n    IF L[mid] = target\n      RETURN mid\n    ELSE IF L[mid] < target\n      low ← mid + 1\n    ELSE\n      high ← mid − 1\n    END IF\n  END WHILE\n\n  RETURN -1\nEND PROCEDURE",
            36: "n ← LENGTH(L)\nk ← k MOD n\nR ← []\n\nFOR i ← n − k + 1 TO n\n  APPEND(R, L[i])\nEND FOR\nFOR i ← 1 TO n − k\n  APPEND(R, L[i])\nEND FOR",
            37: "FOR i ← 1 TO LENGTH(L)\n  FOR j ← i + 1 TO LENGTH(L)\n    IF L[i] + L[j] = target\n      RETURN [L[i], L[j]]\n    END IF\n  END FOR\nEND FOR\nRETURN [-1, -1]",
            38: "best ← W[1]\nFOR EACH word IN W\n  IF LENGTH(word) > LENGTH(best)\n    best ← word\n  END IF\nEND FOR\nDISPLAY best",
            39: 'result ← ""\ni ← 1\n\nWHILE i ≤ LENGTH(s)\n  ch ← s[i]\n  count ← 1\n\n  WHILE i + 1 ≤ LENGTH(s) AND s[i + 1] = ch\n    count ← count + 1\n    i ← i + 1\n  END WHILE\n\n  result ← result + ch + count\n  i ← i + 1\nEND WHILE\n\nRETURN result',
            40: "S ← COPY(L)\nSORT(S)\n\ndiff ← []\nFOR i ← 1 TO LENGTH(L)\n  IF L[i] ≠ S[i]\n    APPEND(diff, i)\n  END IF\nEND FOR\n\nIF LENGTH(diff) = 0\n  RETURN true\nEND IF\n\nIF LENGTH(diff) = 2\n  i ← diff[1]\n  j ← diff[2]\n  temp ← L[i]\n  L[i] ← L[j]\n  L[j] ← temp\n\n  IF L = S\n    RETURN true\n  END IF\nEND IF\n\nRETURN false",

            # LEVEL 5
            41: "visited ← []\ncurrent ← 1\n\nWHILE current ≠ -1\n  FOR EACH v IN visited\n    IF v = current\n      RETURN true\n    END IF\n  END FOR\n\n  APPEND(visited, current)\n  current ← nextIndex[current]\nEND WHILE\n\nRETURN false",
            42: "queue ← []\nvisited ← []\n\nIF grid[1][1] = 1\n  RETURN false\nEND IF\n\nAPPEND(queue, (1,1))\nAPPEND(visited, (1,1))\n\nWHILE LENGTH(queue) > 0\n  (r,c) ← REMOVEFIRST(queue)\n\n  IF r = rows AND c = cols\n    RETURN true\n  END IF\n\n  FOR EACH (nr,nc) IN [(r+1,c),(r-1,c),(r,c+1),(r,c-1)]\n    IF 1 ≤ nr ≤ rows AND 1 ≤ nc ≤ cols\n      IF grid[nr][nc] = 0\n        seen ← false\n        FOR EACH p IN visited\n          IF p = (nr,nc)\n            seen ← true\n          END IF\n        END FOR\n        IF seen = false\n          APPEND(visited, (nr,nc))\n          APPEND(queue, (nr,nc))\n        END IF\n      END IF\n    END IF\n  END FOR\nEND WHILE\n\nRETURN false",
            43: 'PROCEDURE Encrypt(message, k)\n  result ← ""\n  FOR EACH ch IN message\n    IF ch IS LETTER\n      base ← "A" IF ch IS UPPERCASE ELSE "a"\n      pos ← ORD(ch) − ORD(base)\n      newPos ← (pos + k) MOD 26\n      result ← result + CHAR(ORD(base) + newPos)\n    ELSE\n      result ← result + ch\n    END IF\n  END FOR\n  RETURN result\nEND PROCEDURE',
            44: "PROCEDURE Decrypt(message, k)\n  RETURN Encrypt(message, 26 − (k MOD 26))\nEND PROCEDURE",
            45: 'balance ← 0\nFOR EACH ch IN s\n  IF ch = "("\n    balance ← balance + 1\n  ELSE\n    balance ← balance − 1\n    IF balance < 0\n      RETURN false\n    END IF\n  END IF\nEND FOR\nRETURN balance = 0',
            46: "marked ← []\nFOR i ← 0 TO n\n  APPEND(marked, false)\nEND FOR\n\np ← 2\nWHILE p * p ≤ n\n  IF marked[p] = false\n    m ← p * p\n    WHILE m ≤ n\n      marked[m] ← true\n      m ← m + p\n    END WHILE\n  END IF\n  p ← p + 1\nEND WHILE\n\nFOR i ← 2 TO n\n  IF marked[i] = false\n    DISPLAY i\n  END IF\nEND FOR",
            47: "PROCEDURE FirstWins(n)\n  IF n MOD 3 = 0\n    RETURN false\n  ELSE\n    RETURN true\n  END IF\nEND PROCEDURE",
            48: 'names ← []\nbalances ← []\n\nFOR EACH (name, amount) IN T\n  idx ← -1\n  FOR i ← 1 TO LENGTH(names)\n    IF names[i] = name\n      idx ← i\n    END IF\n  END FOR\n\n  IF idx = -1\n    APPEND(names, name)\n    APPEND(balances, amount)\n  ELSE\n    balances[idx] ← balances[idx] + amount\n  END IF\nEND FOR\n\nFOR i ← 1 TO LENGTH(names)\n  DISPLAY names[i] + ": " + balances[i]\nEND FOR',
            49: "FOR i ← 1 TO LENGTH(S) - 1\n  FOR j ← i + 1 TO LENGTH(S)\n    IF LENGTH(S[j]) < LENGTH(S[i])\n      temp ← S[i]\n      S[i] ← S[j]\n      S[j] ← temp\n    ELSE IF LENGTH(S[j]) = LENGTH(S[i]) AND S[j] < S[i]\n      temp ← S[i]\n      S[i] ← S[j]\n      S[j] ← temp\n    END IF\n  END FOR\nEND FOR",
            50: "k ← 1\nWHILE true\n  found ← false\n  FOR EACH x IN L\n    IF x = k\n      found ← true\n    END IF\n  END FOR\n\n  IF found = false\n    RETURN k\n  END IF\n\n  k ← k + 1\nEND WHILE",
        }

        # Optional: level labels (nice for debugging)
        LEVEL_BY_ID = {}
        for qid in range(1, 11):
            LEVEL_BY_ID[qid] = "level1"
        for qid in range(11, 21):
            LEVEL_BY_ID[qid] = "level2"
        for qid in range(21, 31):
            LEVEL_BY_ID[qid] = "level3"
        for qid in range(31, 41):
            LEVEL_BY_ID[qid] = "level4"
        for qid in range(41, 51):
            LEVEL_BY_ID[qid] = "level5"

        existing_ids = {
            q.id for q in PseudocodeQuestionBank.query.with_entities(PseudocodeQuestionBank.id).all()
        }

        seeded = 0
        for qid, ans in ANSWERS.items():
            if qid not in existing_ids:
                continue

            db.session.add(
                PseudocodeAnswerBank(
                    question_id=qid,
                    answer=ans,
                    level=LEVEL_BY_ID.get(qid)
                )
            )
            seeded += 1

        db.session.commit()
        print(f"PseudocodeAnswerBank seeded with {seeded} answers.")