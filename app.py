import os
from flask import Flask, render_template
from dotenv import load_dotenv
from extensions import db, login_manager, jwt, migrate # Import jwt from extensions.py


# Load environment variables from .env file
load_dotenv()

def create_app():
    # Initialize Flask app
    app = Flask(__name__, instance_relative_config=True)
    


    app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # Set max upload size to 1GB

    # Load configuration from instance/config.py
    app.config.from_object('instance.config.Config')

    # Configure JWT Secret Key (IMPORTANT: Use a strong, unique key in production)
    app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY') or "super-secret-jwt-key"

    # NEW: Configure the UPLOAD_FOLDER and ensure the directory exists.
    # This is done after the app object is created, so current_app is not needed.
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads/assignments')
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    app.config['UPLOAD_FOLDERS'] = os.path.join(app.root_path, 'static/uploads/courses')
    if not os.path.exists(app.config['UPLOAD_FOLDERS']):
        os.makedirs(app.config['UPLOAD_FOLDERS'])


    # Initialize extensions with the app instance
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    jwt.init_app(app) # Initialize JWTManager with the app
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Import models here to ensure db is initialized before models are loaded
    from models import User

    # User loader for Flask-Login (for web session management)
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # JWT callbacks (for mobile API token management)
    # These functions tell Flask-JWT-Extended how to identify users from tokens
    # and what claims to put in the token.
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return user.id

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.filter_by(id=identity).one_or_none()

    # Import and register blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.api import api_bp # We'll create this next!

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api') # Register API blueprint with a prefix

    # Basic error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    return app

# This block is for running the app directly during development
if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
