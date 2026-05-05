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
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-key')
    
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
    logger.info("Starting server on 192.168.56.1:5000...")
    serve(app, host='192.168.56.1', port=5000)
