from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.models import db
from app.api import api


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
    db.init_app(app)
    app.register_blueprint(api, url_prefix="/api")
    return app


def create_tables(app):
    with app.app_context():
        db.create_all()
