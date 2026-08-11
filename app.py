from datetime import timedelta
from flask import Flask
from config import Config, validate_config
from routes.auth_routes import auth_bp
from routes.doctor_routes import doctor_bp
from routes.admin_routes import admin_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.permanent_session_lifetime = timedelta(hours=8)

    validate_config()

    app.register_blueprint(auth_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
