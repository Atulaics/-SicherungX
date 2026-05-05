from flask import Flask
from routes import main_bp, api_bp, login_manager
import os
from dotenv import load_dotenv
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

logger = setup_logger('flask_app', 'backend.log')

def create_app():
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dashboard', 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dashboard', 'static'))
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    if not app.config['SECRET_KEY'] and os.getenv('FLASK_ENV') != 'development':
        raise ValueError("CRITICAL: No SECRET_KEY set for production environment!")
    elif not app.config['SECRET_KEY']:
        app.config['SECRET_KEY'] = 'default-dev-key'
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    logger.info("Flask Application initialized.")
    return app

if __name__ == '__main__':
    from database.db_init import init_db
    init_db() # Run DB Init
    app = create_app()
    from waitress import serve
    host_ip = os.getenv('HOST_IP', '0.0.0.0')
    logger.info(f"Starting server on {host_ip}:5000...")
    serve(app, host=host_ip, port=5000)
