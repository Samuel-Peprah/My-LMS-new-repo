# extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_jwt_extended import JWTManager # Import JWTManager
from flask_migrate import Migrate

# Initialize extensions without passing the app instance yet
db = SQLAlchemy()
login_manager = LoginManager()
jwt = JWTManager() # Initialize JWTManager
migrate = Migrate()
