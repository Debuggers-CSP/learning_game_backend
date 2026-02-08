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

        # If already seeded, ensure it matches the action-based model
        existing = PseudocodeQuestionBank.query.first()
        if existing:
            sample_texts = [
                existing.level1 or "",
                existing.level2 or "",
                existing.level3 or "",
                existing.level4 or "",
                existing.level5 or "",
            ]
            has_action_model = any("action" in (text or "").lower() for text in sample_texts)
            if has_action_model:
                print("✅ PseudocodeQuestionBank ready (already has data).")
                return
            print("⚠️ Legacy questions detected. Dropping & recreating PseudocodeQuestionBank only...")
            PseudocodeQuestionBank.__table__.drop(db.engine, checkfirst=True)
            PseudocodeQuestionBank.__table__.create(db.engine, checkfirst=True)

        # ----------------------------
        # ACTION-BASED QUESTIONS (50 total)
        # ----------------------------

        level1_questions = [
            "Actions: MOVE, HIT_WALL, MOVE. Result = score starts at 0. Loop once per action; if MOVE add 1, if HIT_WALL subtract 1. Output final result.",
            "Actions: PICK_KEY, MOVE, OPEN_DOOR. Result = doorState starts 'locked'. Loop once per action; if PICK_KEY set hasKey true, if OPEN_DOOR and hasKey set doorState 'opened'. Output final result.",
            "Actions: MOVE_UP, MOVE_DOWN, REACHED_EXIT. Result = status starts 'playing'. Loop once per action; if REACHED_EXIT set status 'win'. Output final result.",
            "Actions: HIT_WALL, HIT_WALL, MOVE. Result = damage starts 0. Loop once per action; if HIT_WALL add 1. Output final result.",
            "Actions: MOVE, MOVE, MOVE. Result = steps starts 0. Loop once per action; if MOVE add 1. Output final result.",
            "Actions: PICK_KEY, PICK_KEY, MOVE. Result = keys starts 0. Loop once per action; if PICK_KEY add 1. Output final result.",
            "Actions: MOVE, REACHED_EXIT. Result = outcome starts 'none'. Loop once per action; if REACHED_EXIT set outcome 'exit'. Output final result.",
            "Actions: HIT_WALL, MOVE, HIT_WALL. Result = hits starts 0. Loop once per action; if HIT_WALL add 1. Output final result.",
            "Actions: MOVE, MOVE, HIT_WALL, MOVE. Result = score starts 0. Loop once per action; MOVE +1, HIT_WALL -1. Output final result.",
            "Actions: OPEN_DOOR. Result = doorState starts 'locked'. Loop once per action; if OPEN_DOOR set doorState 'opened'. Output final result."
        ]

        level2_questions = [
            "Actions: MOVE, PICK_KEY, MOVE, HIT_WALL, OPEN_DOOR, REACHED_EXIT. Result = score starts 0. Loop once per action; MOVE +1, HIT_WALL -2, REACHED_EXIT +5. Output final result.",
            "Actions: MOVE, MOVE, PICK_KEY, MOVE, OPEN_DOOR. Result = state starts 'locked'. Loop once per action; PICK_KEY sets hasKey, OPEN_DOOR with hasKey sets state 'opened'. Output final result.",
            "Actions: HIT_WALL, MOVE, MOVE, HIT_WALL, MOVE. Result = lives starts 3. Loop once per action; HIT_WALL subtract 1, MOVE no change. Output final result.",
            "Actions: PICK_KEY, MOVE, MOVE, OPEN_DOOR, MOVE, REACHED_EXIT. Result = status starts 'playing'. Loop once per action; REACHED_EXIT sets status 'win'. Output final result.",
            "Actions: MOVE, PICK_KEY, HIT_WALL, MOVE, OPEN_DOOR, MOVE. Result = score starts 0. Loop once per action; MOVE +1, HIT_WALL -1, PICK_KEY +2. Output final result.",
            "Actions: MOVE, MOVE, MOVE, HIT_WALL, MOVE, MOVE. Result = steps starts 0. Loop once per action; MOVE +1, HIT_WALL no change. Output final result.",
            "Actions: PICK_KEY, PICK_KEY, MOVE, OPEN_DOOR, HIT_WALL. Result = keys starts 0. Loop once per action; PICK_KEY +1, OPEN_DOOR uses a key, HIT_WALL no change. Output final result.",
            "Actions: MOVE, HIT_WALL, MOVE, REACHED_EXIT, MOVE. Result = score starts 0. Loop once per action; MOVE +1, HIT_WALL -1, REACHED_EXIT +5. Output final result.",
            "Actions: MOVE, MOVE, HIT_WALL, PICK_KEY, OPEN_DOOR. Result = doorState starts 'locked'. Loop once per action; PICK_KEY sets hasKey, OPEN_DOOR with hasKey sets doorState 'opened'. Output final result.",
            "Actions: MOVE, HIT_WALL, MOVE, HIT_WALL, MOVE, REACHED_EXIT. Result = damage starts 0. Loop once per action; HIT_WALL +1. Output final result."
        ]

        level3_questions = [
            "Actions: MOVE, PICK_KEY, HIT_WALL, UNKNOWN_ACTION, MOVE, OPEN_DOOR, MOVE, REACHED_EXIT. Result = status starts 'playing'. Loop once per action; handle unknown actions safely; output final result.",
            "Actions can be empty. If no actions, result should stay 'none'. Otherwise loop once per action; interpret MOVE (+1 score) and HIT_WALL (-1 score). Output final result.",
            "Actions: MOVE, MOVE, HIT_WALL, PICK_KEY, OPEN_DOOR, HIT_WALL, REACHED_EXIT, MOVE. Result = score starts 0. Loop once per action; update score each time; output final result.",
            "Actions: PICK_KEY, MOVE, OPEN_DOOR, MOVE, OPEN_DOOR, REACHED_EXIT, MOVE, HIT_WALL. Result = doorState starts 'locked'. Loop once per action; if OPEN_DOOR and no key keep locked; output final result.",
            "Actions: HIT_WALL, HIT_WALL, MOVE, MOVE, UNKNOWN_ACTION, MOVE, REACHED_EXIT, MOVE. Result = lives starts 3. Loop once per action; HIT_WALL -1, unknown action no change. Output final result.",
            "Actions: MOVE, MOVE, MOVE, MOVE, MOVE, MOVE, MOVE, MOVE. Result = steps starts 0. Loop once per action; MOVE +1. Output final result.",
            "Actions: PICK_KEY, PICK_KEY, OPEN_DOOR, OPEN_DOOR, MOVE, REACHED_EXIT, UNKNOWN_ACTION, MOVE. Result = keys starts 0. Loop once per action; PICK_KEY +1, OPEN_DOOR uses a key if available. Output final result.",
            "Actions: MOVE, HIT_WALL, MOVE, HIT_WALL, MOVE, HIT_WALL, MOVE, REACHED_EXIT. Result = damage starts 0. Loop once per action; HIT_WALL +1. Output final result.",
            "Actions: MOVE, UNKNOWN_ACTION, MOVE, UNKNOWN_ACTION, MOVE, REACHED_EXIT, MOVE, HIT_WALL. Result = score starts 0. Loop once per action; unknown actions should not crash; output final result.",
            "Actions: MOVE, PICK_KEY, MOVE, PICK_KEY, OPEN_DOOR, MOVE, REACHED_EXIT, HIT_WALL. Result = status starts 'playing'. Loop once per action; track keys and update status. Output final result."
        ]

        level4_questions = [
            "Actions: MOVE, PICK_KEY, HIT_WALL, MOVE, OPEN_DOOR, MOVE, REACHED_EXIT, MOVE, HIT_WALL. Results = score and state. Loop once per action; update score and state; output final results.",
            "Actions may include UNKNOWN_ACTION. Result = status starts 'playing'. Loop once per action; use if/else to handle known actions and a default for unknown. Output final result.",
            "Actions: MOVE, MOVE, PICK_KEY, MOVE, OPEN_DOOR, HIT_WALL, MOVE, REACHED_EXIT, MOVE. Results = score and hasKey. Loop once per action; update both; output final results.",
            "Actions: HIT_WALL, HIT_WALL, HIT_WALL, MOVE, MOVE, REACHED_EXIT, MOVE, MOVE. Result = lives starts 3 and score starts 0. Loop once per action; update both; output final results.",
            "Actions: PICK_KEY, MOVE, PICK_KEY, OPEN_DOOR, OPEN_DOOR, MOVE, REACHED_EXIT, MOVE. Results = keys and doorState. Loop once per action; update both; output final results.",
            "Actions: MOVE, MOVE, MOVE, HIT_WALL, MOVE, HIT_WALL, MOVE, HIT_WALL, MOVE. Result = damage starts 0 and steps starts 0. Loop once per action; update both; output final results.",
            "Actions: MOVE, UNKNOWN_ACTION, MOVE, PICK_KEY, OPEN_DOOR, UNKNOWN_ACTION, MOVE, REACHED_EXIT. Results = score and status. Loop once per action; handle unknown actions safely; output final results.",
            "Actions: OPEN_DOOR, MOVE, OPEN_DOOR, PICK_KEY, OPEN_DOOR, MOVE, REACHED_EXIT, MOVE. Results = hasKey and doorState. Loop once per action; update both; output final results.",
            "Actions: MOVE, HIT_WALL, MOVE, HIT_WALL, PICK_KEY, MOVE, OPEN_DOOR, REACHED_EXIT. Results = score and doorState. Loop once per action; update both; output final results.",
            "Actions can be empty. Results = score and status. If empty, keep defaults; otherwise loop once per action and update. Output final results."
        ]

        level5_questions = [
            "Final mastery: Gather all actions in order. Define what the result represents. Loop once per action, use if/else to interpret each action, update the result, and output the final result. Handle unknown actions safely.",
            "Final mastery: Actions may be empty or include UNKNOWN_ACTION. Design the full algorithm: loop once per action, decide with if/else, update result(s), output final result(s).",
            "Final mastery: Given an ordered action list from a maze run, build the algorithm that processes each action, updates result state, and outputs the final result. Handle unknown actions.",
            "Final mastery: Create a complete action-processing algorithm that loops once per action, uses decisions for each action type, updates results consistently, and outputs the final result.",
            "Final mastery: Write the full action-based algorithm. Define result, loop per action, interpret with if/else, update result, output final result. Include a safe default for unknown actions.",
            "Final mastery: Design the solution for action-based scoring. Loop once per action, update score/state, output final result, and handle unknown actions.",
            "Final mastery: Build the complete action-processing flow. Gather actions, loop once per action, interpret each action, update result, output final result.",
            "Final mastery: Create the final code answer pattern using actions and results. Loop once per action, decide with if/else, update result, output final result.",
            "Final mastery: Show the full algorithm for actions-in-order. Handle empty action list, unknown actions, and output the final result.",
            "Final mastery: Produce the final algorithm structure: gather actions, loop once per action, interpret actions, update result(s), output final result(s)."
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
