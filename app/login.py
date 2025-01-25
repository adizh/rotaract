from flask import Flask, request, jsonify,Blueprint
from flask_cors import CORS
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token
import mysql.connector
from dotenv import load_dotenv
import os
from app.hash import verify_password
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:4500"}})  # Allow all origins for testing
login_bp = Blueprint('login', __name__)
# MySQL Database configuration

load_dotenv()
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_ROOT'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

@login_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        response = jsonify()
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.status_code = 200
        return response

    data = request.get_json()
    phone = data.get('phone')
    password = data.get('password')

    if not phone or not password:
        return jsonify({'error': 'Phone and password are required'}), 400

    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)

        # Query to fetch user and groupId
        query = """
    SELECT 
        users.*, 
        teams.groupId, 
        teams.groupName, 
        volunteers.firstName AS teamLeaderFirstName, 
        volunteers.lastName AS teamLeaderLastName
    FROM 
        users
    LEFT JOIN 
        teams 
        ON users.id = teams.teamLeaderId
    LEFT JOIN 
        volunteers 
        ON teams.teamLeaderId = volunteers.id
    WHERE 
        users.phone = %s
    """
        cursor.execute(query, (phone,))
        user = cursor.fetchone()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not verify_password(password, user['password']):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Return user details along with groupId
        return jsonify({
            'message': "Success",
            'user': user
        }), 200

    except mysql.connector.Error as err:
        print("Database error:", str(err))
        return jsonify({'error': 'Database error', 'details': str(err)}), 500

    finally:
        try:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
        except Exception as close_err:
            print("Error during resource cleanup:", str(close_err))




@login_bp.route('/fetch-user-by-id/<string:user_id>', methods=['GET'])
def fetch_user_by_id(user_id):
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)

        # Fetch user details
        with connection.cursor(dictionary=True) as cursor:
            query = """
                SELECT id, role, phone
                FROM users
                WHERE id = %s
            """
            cursor.execute(query, (user_id,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"error": "User not found"}), 404

            # Fully fetch any remaining results (if applicable)
            cursor.fetchall()

        # If the role includes 'leader', fetch groupId from teams
        if 'leader' in user['role']:
            with connection.cursor(dictionary=True) as cursor:
                query = """
                    SELECT 
                        teams.groupId,
                        teams.groupName,
                        teams.status,
                        teams.projectName,
                        volunteers.firstName,
                        volunteers.lastName
                    FROM 
                        teams
                    LEFT JOIN 
                        volunteers
                        ON teams.teamLeaderId = volunteers.id
                    WHERE 
                        teams.teamLeaderId = %s
                """
                cursor.execute(query, (user_id,))
                team_details = cursor.fetchone()

                if team_details:
                    user.update(team_details)

                # Fully fetch any remaining results
                cursor.fetchall()

        return jsonify(user)

    except mysql.connector.Error as err:
        # Log the error for debugging
        app.logger.error(f"MySQL Error: {err}")
        return jsonify({"error": "Database query failed"}), 500

    except Exception as e:
        # Log any other exceptions
        app.logger.error(f"Unhandled Exception: {e}")
        return jsonify({"error": "An error occurred"}), 500

    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
