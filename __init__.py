# __init__.py

from flask import Flask
from flask_login import LoginManager
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Setup of key Flask object (app)
app = Flask(__name__)

# Configure Flask Port, default to 8320 which is same as Docker setup
app.config["FLASK_PORT"] = int(os.environ.get("FLASK_PORT") or 8320)

# Configure Flask to handle JSON with UTF-8 encoding versus default ASCII
app.config["JSON_AS_ASCII"] = False  # Allow emojis, non-ASCII characters in JSON responses

# Initialize Flask-Login object
login_manager = LoginManager()
login_manager.init_app(app)

# -------------------------
# CORS (IMPORTANT)
# -------------------------
ALLOWED_ORIGINS = [
    "http://localhost:4500",
    "http://127.0.0.1:4500",
    "http://localhost:4600",
    "http://127.0.0.1:4600",
    "http://localhost:4000",
    "http://127.0.0.1:4000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "https://open-coding-society.github.io",
    "https://pages.opencodingsociety.com",
    "https://debuggers-csp.github.io",
    "http://robop.opencodingsociety.com",
    "https://robop.opencodingsociety.com",
]

# Apply CORS ONLY to API routes
# Key points:
# - restrict to /api/* so assets/pages aren’t affected
# - include OPTIONS for preflight
# - vary Origin to keep caches correct
cors = CORS(
    app,
    supports_credentials=True,
    resources={
        r"/api/*": {
            "origins": ALLOWED_ORIGINS,
        }
    },
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ✅ ADD THIS BACK (it helps cookies across origins if you ever use login sessions)
@app.after_request
def add_cors_headers(response):
    origin = response.headers.get("Access-Control-Allow-Origin")
    if origin:
        response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Vary"] = "Origin"
    return response

# -------------------------
# Admin Defaults
# -------------------------
app.config["ADMIN_USER"] = os.environ.get("ADMIN_USER") or "Admin Name"
app.config["ADMIN_UID"] = os.environ.get("ADMIN_UID") or "admin"
app.config["ADMIN_PASSWORD"] = (
    os.environ.get("ADMIN_PASSWORD") or os.environ.get("DEFAULT_PASSWORD") or "password"
)
app.config["ADMIN_PFP"] = os.environ.get("ADMIN_PFP") or "default.png"

# Default User Defaults
app.config["DEFAULT_USER"] = os.environ.get("DEFAULT_USER") or "User Name"
app.config["DEFAULT_UID"] = os.environ.get("DEFAULT_UID") or "user"
app.config["DEFAULT_USER_PASSWORD"] = (
    os.environ.get("DEFAULT_USER_PASSWORD") or os.environ.get("DEFAULT_PASSWORD") or "password"
)
app.config["DEFAULT_USER_PFP"] = os.environ.get("DEFAULT_USER_PFP") or "default.png"

# Reset Defaults
app.config["DEFAULT_PASSWORD"] = os.environ.get("DEFAULT_PASSWORD") or "password"
app.config["DEFAULT_PFP"] = os.environ.get("DEFAULT_PFP") or "default.png"

# -------------------------
# Browser settings
# -------------------------
SECRET_KEY = os.environ.get("SECRET_KEY") or "SECRET_KEY"  # secret key for session management
SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME") or "sess_python_flask"
JWT_TOKEN_NAME = os.environ.get("JWT_TOKEN_NAME") or "jwt_python_flask"
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SESSION_COOKIE_NAME"] = SESSION_COOKIE_NAME
app.config["JWT_TOKEN_NAME"] = JWT_TOKEN_NAME

# In local dev over http, Secure cookies are not sent. Enable Secure+SameSite=None only in prod.
_env_is_production = str(os.environ.get("IS_PRODUCTION", "")).strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}
app.config["IS_PRODUCTION"] = _env_is_production
app.config["SESSION_COOKIE_SAMESITE"] = "None" if app.config["IS_PRODUCTION"] else "Lax"
app.config["SESSION_COOKIE_SECURE"] = True if app.config["IS_PRODUCTION"] else False

# -------------------------
# Database settings
# -------------------------
IS_PRODUCTION = app.config["IS_PRODUCTION"]
dbName = "user_management"
DB_ENDPOINT = os.environ.get("DB_ENDPOINT") or None
DB_USERNAME = os.environ.get("DB_USERNAME") or None
DB_PASSWORD = os.environ.get("DB_PASSWORD") or None

if DB_ENDPOINT and DB_USERNAME and DB_PASSWORD:
    # Production - Use MySQL
    DB_PORT = "3306"
    dbString = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_ENDPOINT}:{DB_PORT}"
    dbURI = dbString + "/" + dbName
    backupURI = None  # MySQL backup would require a different approach
else:
    # Development - Use SQLite (ABSOLUTE PATH so it always goes to the same place)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    volumes_dir = os.path.join(base_dir, "volumes")
    os.makedirs(volumes_dir, exist_ok=True)

    db_path = os.path.join(volumes_dir, f"{dbName}.db")
    bak_path = os.path.join(volumes_dir, f"{dbName}_bak.db")

    dbURI = "sqlite:///" + db_path
    backupURI = "sqlite:///" + bak_path

    # keep these for display/debug
    dbString = "sqlite:///" + volumes_dir + "/"

# Set database configuration in Flask app
app.config["DB_ENDPOINT"] = DB_ENDPOINT
app.config["DB_USERNAME"] = DB_USERNAME
app.config["DB_PASSWORD"] = DB_PASSWORD
app.config["SQLALCHEMY_DATABASE_NAME"] = dbName
app.config["SQLALCHEMY_DATABASE_STRING"] = dbString
app.config["SQLALCHEMY_DATABASE_URI"] = dbURI
app.config["SQLALCHEMY_BACKUP_URI"] = backupURI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# -------------------------
# Image upload settings
# -------------------------
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # maximum size of uploaded content
app.config["UPLOAD_EXTENSIONS"] = [".jpg", ".png", ".gif"]  # supported file types
app.config["UPLOAD_FOLDER"] = os.path.join(app.instance_path, "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Data folder for shared file-based storage
app.config["DATA_FOLDER"] = os.path.join(app.instance_path, "data")
os.makedirs(app.config["DATA_FOLDER"], exist_ok=True)

# -------------------------
# GITHUB settings
# -------------------------
app.config["GITHUB_API_URL"] = "https://api.github.com"
app.config["GITHUB_TOKEN"] = os.environ.get("GITHUB_TOKEN") or None
app.config["GITHUB_TARGET_TYPE"] = os.environ.get("GITHUB_TARGET_TYPE") or "user"
app.config["GITHUB_TARGET_NAME"] = os.environ.get("GITHUB_TARGET_NAME") or "open-coding-society"

# -------------------------
# OpenAI (ChatGPT) settings
# -------------------------
app.config["OPENAI_SERVER"] = os.environ.get("OPENAI_SERVER") or "https://api.openai.com/v1/chat/completions"
app.config["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY") or None
app.config["OPENAI_MODEL"] = os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"

# -------------------------
# PIKA (Video) settings
# -------------------------
app.config["PIKA_SERVER"] = os.environ.get("PIKA_SERVER") or None
app.config["PIKA_API_KEY"] = os.environ.get("PIKA_API_KEY") or None
app.config["PIKA_STATUS_SERVER"] = os.environ.get("PIKA_STATUS_SERVER") or None
app.config["PIKA_MODEL"] = os.environ.get("PIKA_MODEL") or None

# -------------------------
# Endgame settings
# -------------------------
app.config["FINAL_CODE_ANSWER"] = os.environ.get("FINAL_CODE_ANSWER") or (
    "To earn mastery, do the following: "
    "Define what the result represents. "
    "Gather every action in order. "
    "Create a loop that runs once per action. "
    "Each time the loop runs, read the current action, decide what it means, "
    "and update the result. "
    "If an action is unknown, handle it safely. "
    "When the loop ends, output the final result."
)

# -------------------------
# KASM settings
# -------------------------
app.config["KASM_SERVER"] = os.environ.get("KASM_SERVER") or "https://kasm.opencodingsociety.com"
app.config["KASM_API_KEY"] = os.environ.get("KASM_API_KEY") or None
app.config["KASM_API_KEY_SECRET"] = os.environ.get("KASM_API_KEY_SECRET") or None

# -------------------------
# GROQ settings
# -------------------------
app.config["GROQ_API_KEY"] = os.environ.get("GROQ_API_KEY") or None


# ============================================================
# ✅ PSEUDOCODE BANKS: register models + create tables + seed
# ============================================================
# WHY THIS IS NEEDED:
# - SQLAlchemy only creates tables for models it has imported
# - so we import the model modules, then run db.create_all()
# - then seed question bank first, answer bank second

def init_app_db_and_seed():
    """
    Call once at import/startup.
    Creates tables and seeds pseudocode question+answer banks.
    """
    with app.app_context():
        # Import models so SQLAlchemy "registers" them
        try:
            from model.pseudocode_bank import initPseudocodeQuestionBank  # noqa: F401
        except Exception as e:
            print("⚠️ Could not import model.pseudocode_bank:", e)
            initPseudocodeQuestionBank = None

        try:
            # IMPORTANT: adjust import if your filename is different
            # If your model file is model/pseudocodeanswer_bank.py this is correct:
            from model.pseudocodeanswer1_bank import initPseudocodeAnswerBank  # noqa: F401
        except Exception as e:
            print("⚠️ Could not import model.pseudocodeanswer_bank:", e)
            initPseudocodeAnswerBank = None

        # Create all tables for all imported models
        try:
            db.create_all()
        except Exception as e:
            print("❌ db.create_all() failed:", e)

        # Seed question bank
        if initPseudocodeQuestionBank:
            try:
                initPseudocodeQuestionBank(force_recreate=False)
            except Exception as e:
                print("⚠️ initPseudocodeQuestionBank failed:", e)

        # Seed answer bank
        if initPseudocodeAnswerBank:
            try:
                initPseudocodeAnswerBank(force_recreate=False)
            except Exception as e:
                print("⚠️ initPseudocodeAnswerBank failed:", e)

        # Print tables to confirm
        try:
            from sqlalchemy import inspect
            print("✅ DB URI:", app.config.get("SQLALCHEMY_DATABASE_URI"))
            print("✅ Tables:", inspect(db.engine).get_table_names())
        except Exception as e:
            print("⚠️ Could not list tables:", e)


# Run once on startup
init_app_db_and_seed()