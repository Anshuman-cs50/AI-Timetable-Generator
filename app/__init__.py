from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        from app.routes import main
        from app.auth import auth
        app.register_blueprint(main)
        app.register_blueprint(auth)
        
        from app.models import User
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
            
        try:
            db.create_all()
            print("Database initialized successfully.")
        except Exception as e:
            print(f"Error during database initialization: {e}")
            # On serverless, we might want to continue and let it fail on-route 
            # instead of crashing the entire function startup

    return app
