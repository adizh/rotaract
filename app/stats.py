from flask import Flask, request, jsonify,Blueprint
from flask_cors import CORS
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token
import mysql.connector
import os
from app.hash import verify_password
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:4500"}})  # Allow all origins for testing
stats_py = Blueprint('stats', __name__)
# MySQL Database configuration
