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
app.config['FLASK_PORT'] = int(os.environ.get('FLASK_PORT') or 8320)

# Configure Flask to handle JSON with UTF-8 encoding versus default ASCII
app.config['JSON_AS_ASCII'] = False  # Allow emojis, non-ASCII characters in JSON responses


# Initialize Flask-Login object
login_manager = LoginManager()
login_manager.init_app(app)


# Allowed servers for cross-origin resource sharing (CORS)
cors = CORS(
   app,
   supports_credentials=True,
   origins=[
       'http://localhost:4500',
       'http://127.0.0.1:4500',
       'http://localhost:4600',
       'http://127.0.0.1:4600',
       'http://localhost:4000',
       'http://127.0.0.1:4000',
         'http://localhost:3000',
         'http://127.0.0.1:3000',
         'http://localhost:5173',
         'http://127.0.0.1:5173',
         'http://localhost:5500',
         'http://127.0.0.1:5500',
         'http://localhost:8080',
         'http://127.0.0.1:8080',
         'http://localhost:8081',
         'http://127.0.0.1:8081',
       'https://open-coding-society.github.io',
       'https://pages.opencodingsociety.com',
   ],
   methods=["GET", "POST", "PUT", "OPTIONS"]
)


# Admin Defaults
app.config['ADMIN_USER'] = os.environ.get('ADMIN_USER') or 'Admin Name'
app.config['ADMIN_UID'] = os.environ.get('ADMIN_UID') or 'admin'
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD') or os.environ.get('DEFAULT_PASSWORD') or 'password'
app.config['ADMIN_PFP'] = os.environ.get('ADMIN_PFP') or 'default.png'
# Default User Defaults
app.config['DEFAULT_USER'] = os.environ.get('DEFAULT_USER') or 'User Name'
app.config['DEFAULT_UID'] = os.environ.get('DEFAULT_UID') or 'user'
app.config['DEFAULT_USER_PASSWORD'] = os.environ.get('DEFAULT_USER_PASSWORD') or os.environ.get('DEFAULT_PASSWORD') or 'password'
app.config['DEFAULT_USER_PFP'] = os.environ.get('DEFAULT_USER_PFP') or 'default.png'
# Reset Defaults
app.config['DEFAULT_PASSWORD'] = os.environ.get('DEFAULT_PASSWORD') or 'password'
app.config['DEFAULT_PFP'] = os.environ.get('DEFAULT_PFP') or 'default.png'


# Browser settings
SECRET_KEY = os.environ.get('SECRET_KEY') or 'SECRET_KEY' # secret key for session management
SESSION_COOKIE_NAME = os.environ.get('SESSION_COOKIE_NAME') or 'sess_python_flask'
JWT_TOKEN_NAME = os.environ.get('JWT_TOKEN_NAME') or 'jwt_python_flask'
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_NAME'] = SESSION_COOKIE_NAME
app.config['JWT_TOKEN_NAME'] = JWT_TOKEN_NAME


# Database settings
IS_PRODUCTION = os.environ.get('IS_PRODUCTION') or None
dbName = 'user_management'
DB_ENDPOINT = os.environ.get('DB_ENDPOINT') or None
DB_USERNAME = os.environ.get('DB_USERNAME') or None
DB_PASSWORD = os.environ.get('DB_PASSWORD') or None
if DB_ENDPOINT and DB_USERNAME and DB_PASSWORD:
   # Production - Use MySQL
   DB_PORT = '3306'
   DB_NAME = dbName
   dbString = f'mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_ENDPOINT}:{DB_PORT}'
   dbURI =  dbString + '/' + dbName
   backupURI = None  # MySQL backup would require a different approach
else:
   # Development - Use SQLite
   dbString = 'sqlite:///volumes/'
   dbURI = dbString + dbName + '.db'
   backupURI = dbString + dbName + '_bak.db'
# Set database configuration in Flask app
app.config['DB_ENDPOINT'] = DB_ENDPOINT
app.config['DB_USERNAME'] = DB_USERNAME
app.config['DB_PASSWORD'] = DB_PASSWORD
app.config['SQLALCHEMY_DATABASE_NAME'] = dbName
app.config['SQLALCHEMY_DATABASE_STRING'] = dbString
app.config['SQLALCHEMY_DATABASE_URI'] = dbURI
app.config['SQLALCHEMY_BACKUP_URI'] = backupURI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Image upload settings
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # maximum size of uploaded content
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']  # supported file types
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Data folder for shared file-based storage
app.config['DATA_FOLDER'] = os.path.join(app.instance_path, 'data')
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)


# GITHUB settings
app.config['GITHUB_API_URL'] = 'https://api.github.com'
app.config['GITHUB_TOKEN'] = os.environ.get('GITHUB_TOKEN') or None
app.config['GITHUB_TARGET_TYPE'] = os.environ.get('GITHUB_TARGET_TYPE') or 'user'
app.config['GITHUB_TARGET_NAME'] = os.environ.get('GITHUB_TARGET_NAME') or 'open-coding-society'


# OpenAI (ChatGPT) settings
app.config['OPENAI_SERVER'] = os.environ.get('OPENAI_SERVER') or 'https://api.openai.com/v1/chat/completions'
app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY') or None
app.config['OPENAI_MODEL'] = os.environ.get('OPENAI_MODEL') or 'gpt-4o-mini'

# PIKA (Video) settings
app.config['PIKA_SERVER'] = os.environ.get('PIKA_SERVER') or None
app.config['PIKA_API_KEY'] = os.environ.get('PIKA_API_KEY') or None
app.config['PIKA_STATUS_SERVER'] = os.environ.get('PIKA_STATUS_SERVER') or None
app.config['PIKA_MODEL'] = os.environ.get('PIKA_MODEL') or None

# Endgame settings
app.config['FINAL_CODE_ANSWER'] = os.environ.get('FINAL_CODE_ANSWER') or (
   "To earn mastery, do the following: "
   "Define what the result represents. "
   "Gather every action in order. "
   "Create a loop that runs once per action. "
   "Each time the loop runs, read the current action, decide what it means, "
   "and update the result. "
   "If an action is unknown, handle it safely. "
   "When the loop ends, output the final result."
)


# KASM settings
app.config['KASM_SERVER'] = os.environ.get('KASM_SERVER') or 'https://kasm.opencodingsociety.com'
app.config['KASM_API_KEY'] = os.environ.get('KASM_API_KEY') or None
app.config['KASM_API_KEY_SECRET'] = os.environ.get('KASM_API_KEY_SECRET') or None


#GROQ settings
app.config['GROQ_API_KEY'] = os.environ.get('GROQ_API_KEY')

