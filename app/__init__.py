from flask import Flask
from flask_wtf.csrf import CSRFProtect
import os
import logging

def create_app():
    app = Flask(__name__)

    # Security Configuration
    app.secret_key = os.environ.get('SECRET_KEY', '8f8914969a6246448a7eed278112ed862b73e5ac11f09943e2b20e6b470fa7f1')

    # Cookie Security
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Enable Secure flag only if explicitly set or if likely in production (e.g., Render sets PORT)
    # Default to False for local dev to avoid breaking it
    if os.environ.get('Render') or os.environ.get('FLASK_ENV') == 'production':
        app.config['SESSION_COOKIE_SECURE'] = True
    else:
        app.config['SESSION_COOKIE_SECURE'] = False

    # CSRF Protection
    csrf = CSRFProtect(app)

    from . import routes
    app.register_blueprint(routes.bp)

    # Logging Configuration
    logging.basicConfig(level=logging.INFO)

    return app
