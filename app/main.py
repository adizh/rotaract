from flask import Flask, jsonify, request,Blueprint
import mysql.connector
import uuid
from flask_cors import CORS, cross_origin
import os
app = Flask(__name__)
main_bp = Blueprint('main', __name__)
# Enable CORS for all routes and allow specific frontend origin
CORS(app, resources={r"/*": {"origins": ["http://localhost:4500", "https://rotaract-front-17bdmy7ft-adizhs-projects.vercel.app"]}}) 

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_ROOT'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}
@main_bp.route('/test', methods=['GET'])

def test():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM users"
        cursor.execute(query)

        rows = cursor.fetchall()

        cursor.close()
        connection.close()

        return jsonify(rows)

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    


@main_bp.route('/add_user', methods=['POST', 'OPTIONS'])
def add_user():
   if request.method == 'OPTIONS':
        response = jsonify()
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.status_code = 200  # Ensure it's OK
        return response

   if request.method == 'POST':
        data = request.get_json()
        print("Received data:", data)

        name = data.get('name')
        phone = data.get('phone')
        role = data.get('role')
        id = str(uuid.uuid4()).replace("-", "")[:12]

        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()
            print("Database connection established.")
            query = "INSERT INTO users (id, name, phone, role) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (id, name, phone, role))
            connection.commit()

            cursor.close()
            connection.close()

            return jsonify({
                'status': 'success',
                'message': 'User created',
                # 'data': {
                #     'access_token': access_token,
                #     'refresh_token': refresh_token
                # }
                }), 200 

        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return jsonify({'error': str(err)}), 500


