from flask import Flask, request, jsonify,Blueprint
from flask_cors import CORS
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token

from dotenv import load_dotenv
import os
from pymongo import MongoClient


from app.hash import verify_password
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:4500","https://scintillating-dasik-a1e6aa.netlify.app", "https://rotaract-front-17bdmy7ft-adizhs-projects.vercel.app"]}})  # Allow all origins for testing
login_bp = Blueprint('login', __name__)
# MySQL Database configuration

load_dotenv()
import jwt

client = MongoClient(os.getenv('CONNECTION_STRING'))
SECRET_KEY = os.getenv('SECRET_KEY')
users_collection = client.rotaract['users']

@login_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        # Handle preflight request for CORS
        response = jsonify()
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.status_code = 200
        return response

    # Get data from the request
    data = request.get_json()
    phone = data.get('phone')
    password = data.get('password')

    # Validate input
    if not phone or not password:
        return jsonify({'error': 'Phone and password are required'}), 400

    try:
        # Find user by phone in MongoDB
        user = users_collection.find_one({'phone': phone})

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check if the provided password matches the hashed password
        if not verify_password(password, user['password']):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Create the JWT token
        user_info = {
            'id': str(user['_id']),
            'phone': user['phone'],
            'role': user['role'],
        }

        if 'groupId' in user and user['groupId']:
            user_info['groupId'] = user['groupId']

        # Set expiration (you can omit it for a token that never expires)
       # expiration_time = datetime.datetime.utcnow() + datetime.timedelta(days=30)  # Token expires in 30 days

        token = jwt.encode(
            {
                'sub': user_info['id'],  # Subject of the token, usually the user id
               # 'exp': expiration_time  # Expiration time
            },
            SECRET_KEY,
            algorithm='HS256'  # The algorithm used to encode the JWT
        )

        return jsonify({
            'message': "Login successful",
            'user': user_info,
            'token': token  # Return the JWT token to the client
        }), 200

    except Exception as e:
        print("Error:", str(e))
        return jsonify({'error': 'An error occurred', 'details': str(e)}), 500


@login_bp.route('/fetch-user-by-id/<string:user_id>', methods=['GET'])
def fetch_user_by_id(user_id):
    try:
        # MongoDB aggregation pipeline
        pipeline = [
            {
                "$match": {"userId": user_id}  # Match the user by userId (assuming 'userId' is the field name)
            },
            {
                "$lookup": {
                    "from": "teams",  # Look up the teams collection to check if the user is a team leader
                    "localField": "userId",  # Match the user's userId
                    "foreignField": "teamLeaderId",  # Match the team leader's ID in the teams collection
                    "as": "teamDetails"  # Store matched team details in the 'teamDetails' field
                }
            },
            {
                "$unwind": {
                    "path": "$teamDetails",
                    "preserveNullAndEmptyArrays": True  # Allow users who are not team leaders
                }
            },
            {
                "$lookup": {
                    "from": "volunteers",  # Look up the volunteers collection to get the volunteer's name (firstName, lastName)
                    "localField": "teamDetails.teamLeaderId",  # Match the team leader's ID
                    "foreignField": "userId",  # Match the 'userId' field in volunteers collection
                    "as": "teamLeader"
                }
            },
            {
                "$unwind": {
                    "path": "$teamLeader",
                    "preserveNullAndEmptyArrays": True  # Allow users who are not leaders and don't have a team leader
                }
            },
            {
                "$project": {  # Project the required fields
                    "_id": 0,  # Exclude the MongoDB _id field
                    "userId": 1,
                    "role": 1,
                    "phone": 1,
                    "groupId": "$teamDetails.groupId",  # Include team ID if present
                    "teamName": "$teamDetails.groupName",  # Include team name if present
                    "status": "$teamDetails.status",  # Include team status if present
                    "teamProjectName": "$teamDetails.projectName",  # Include project name if present
                    "teamLeader": {
                        "firstName": "$teamLeader.firstName",  # Include team leader's first name
                        "lastName": "$teamLeader.lastName"  # Include team leader's last name
                    }
                }
            }
        ]

        # Execute the aggregation pipeline
        result = list(users_collection.aggregate(pipeline))

        if result:
            # Return the user document (result will contain one document)
            return jsonify(result[0])
        else:
            return jsonify({"error": "User not found"}), 404

    except Exception as e:
        # Log the error for debugging
        app.logger.error(f"Unhandled Exception: {e}")
        return jsonify({"error": "An error occurred"}), 500

