from flask import Flask
from flask_wtf.csrf import CSRFProtect
import os
import logging

def create_app():
    app = Flask(__name__)

    # Security Configuration
    is_prod = os.environ.get('Render') or os.environ.get('FLASK_ENV') == 'production'

    if is_prod:
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY environment variable is required in production!")
        app.secret_key = os.environ.get('SECRET_KEY')
        app.config['SESSION_COOKIE_SECURE'] = True
    else:
        # Fallback for dev only
        app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_change_me_in_prod')
        app.config['SESSION_COOKIE_SECURE'] = False

    # Cookie Security
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # CSRF Protection
    csrf = CSRFProtect(app)

    from . import routes
    app.register_blueprint(routes.bp)

    # Logging Configuration
    logging.basicConfig(level=logging.INFO)

    return app
