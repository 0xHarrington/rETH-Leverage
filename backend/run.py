from flask import Flask
from flask_cors import CORS
from app.models import db
from app.api import api
from seed import create_app


if __name__ == "__main__":
    app = create_app()
    CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}})
    app.run(debug=True, host="0.0.0.0", port=5000)
