from flask import Blueprint, Flask,request, jsonify
import mysql.connector
import uuid
from pymongo import MongoClient
from mysql.connector import Error
from bson import ObjectId
import os
from flask_cors import CORS
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:4500", "https://rotaract-front.vercel.app"]}}) 
# Create a blueprint for volunteers
volunteers_bp = Blueprint('volunteers', __name__)
client = MongoClient(os.getenv('CONNECTION_STRING'))

database = client.rotaract


# @volunteers_bp.route('/get-volunteer-by-id/<int:volunteer_id>', methods=['GET'])
# def get_volunteer_by_id(volunteer_id):
#     try:
#         # Open a connection to the database
#         connection = mysql.connector.connect(**DB_CONFIG)
#         cursor = connection.cursor()

#         # SQL query to get volunteer by ID
#         cursor.execute("""
#             SELECT 
#                 id,
#                 firstName,
#                 lastName,
#                 phone,
#                 joinedAt,
#                 groupId,
#                 numOfMeetings
#             FROM volunteers
#             WHERE id = %s
#         """, (volunteer_id,))

#         # Fetch the result from the query
#         result = cursor.fetchone()

#         if result:
#             # Prepare the response data
#             volunteer = {
#                 'id': result[0],
#                 'firstName': result[1],
#                 'lastName': result[2],
#                 'phone': result[3],
#                 'joinedAt': result[4],
#                 'groupId': result[5],
#                 'numOfMeetings': result[6],
#             }

#             # Close the database connection
#             cursor.close()
#             connection.close()

#             return jsonify(volunteer)  # Return the volunteer data as JSON

#         else:
#             # If no volunteer is found with that ID
#             return jsonify({'error': 'Volunteer not found'}), 404

#     except mysql.connector.Error as err:
#         return jsonify({'error': str(err)}), 500

def convert_objectid_to_string(doc):
    """Convert ObjectId fields to string in a document"""
    if isinstance(doc, dict):
        return {key: (str(value) if isinstance(value, ObjectId) else value) for key, value in doc.items()}
    return doc


from .verify_token import verify_token
@volunteers_bp.route('/get-all', methods=['GET'])
def get_all_volunteers():
    decoded_token = verify_token()
    if decoded_token is None:
         return jsonify({'error': 'Token is invalid or expired'}), 401
    try:
        volunteers = list(database.volunteers.aggregate([
            {
                "$lookup": {
                    "from": "teams",  # Match with teams collection
                    "localField": "groupId",
                    "foreignField": "groupId",
                    "as": "group_info"
                }
            },
            {
                "$unwind": {
                    "path": "$group_info",
                    "preserveNullAndEmptyArrays": True  # Keep volunteers even if no matching team
                }
            },
            {
                "$addFields": {  # Add group object while keeping other fields
                    "group": {
                        "groupId": "$group_info.groupId",
                        "groupName": "$group_info.groupName",
                        "meetingCount": "$group_info.meetingCount"  # Add meeting count from group
                    }
                }
            },
            {
                "$addFields": {  # Calculate performance based on number of meetings
                    "performance": {
                        "$cond": [
                            {"$gt": ["$group.meetingCount", 0]},  # Check if meetingCount > 0
                            {
                                "$multiply": [
                                    {"$divide": ["$numOfMeetings", "$group.meetingCount"]},  # numOfMeetings / meetingCount
                                    100
                                ]
                            },
                            0  # If meetingCount is 0, set performance to 0
                        ]
                    }
                }
            },
            {
                "$project": {
                    "group_info": 0  # Remove extra joined field
                }
            }
        ]))

        # Convert ObjectId to string for serialization
        volunteers = [convert_objectid_to_string(volunteer) for volunteer in volunteers]

        return jsonify(volunteers)

    except Exception as err:
        return jsonify({'error': str(err)}), 500


@volunteers_bp.route('/delete-volunteer/<string:volunteer_id>', methods=['DELETE'])
def delete_volunteer(volunteer_id):
    try:
        # Check if the volunteer exists using the custom `id` field
        volunteer = database.volunteers.find_one({"id": volunteer_id})
        if not volunteer:
            return jsonify({"error": "Volunteer not found"}), 404

        # First, delete the associated tasks
 

        # Then, delete the volunteer from the volunteers collection
        result_volunteer = database.volunteers.delete_one({"id": volunteer_id})

        # Check if any document was deleted
        if result_volunteer.deleted_count > 0:
            return jsonify({"message": "Volunteer and associated tasks deleted successfully"}), 200
        else:
            return jsonify({"error": "Failed to delete volunteer"}), 404

    except Exception as err:
        return jsonify({"error": str(err)}), 500






@volunteers_bp.route('/create-volunteer', methods=['POST'])
def create_volunteer():
    # Get the volunteer data from the request body (JSON format)
    data = request.get_json()
    id = str(uuid.uuid4()).replace("-", "")[:12]

    first_name = data.get('firstName')
    last_name = data.get('lastName')
    phone = data.get('phone')
    joined_at = data.get('joinedAt')
    group_id = data.get('groupId')
    age = data.get('age')

    # Validate the received data (you can add more validation as needed)
    if not first_name or not last_name or not phone or not age:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        # Create the volunteer document
        volunteer = {
            "firstName": first_name,
            "lastName": last_name,
            "phone": phone,
            "joinedAt": joined_at,  # Assuming joinedAt is in YYYY-MM-DD format
            "groupId": group_id,
            "numOfMeetings": 0,
            "id":id ,
            "age":age
        }

        # Insert the document into the MongoDB collection
        result = database.volunteers.insert_one(volunteer)

        # Return a success message
        return jsonify({'message': 'Volunteer created successfully', 'id': str(result.inserted_id)}), 200

    except Exception as err:
        # Return an error message in case of an issue with the database
        return jsonify({'error': str(err)}), 500



from bson import ObjectId
from flask import request, jsonify

@volunteers_bp.route('/update-volunteer/<string:volunteer_id>', methods=['PUT'])
def update_volunteer(volunteer_id):
    try:
        # Convert volunteer_id to ObjectId and check if it exists in the database
   

        volunteer = database.volunteers.find_one({"id": volunteer_id})
        if not volunteer:
            return jsonify({"error": "Volunteer not found"}), 404

        # Get the request data (assuming JSON)
        data = request.get_json()

        # Extract the fields
        first_name = data.get('firstName')
        last_name = data.get('lastName')
        phone = data.get('phone')
        group_id = data.get('groupId')
        joined_at = data.get('joinedAt')
        age = data.get('age')

        # Validate input data
        if not all([first_name, last_name, phone, group_id, joined_at,age]):
            return jsonify({"error": "All fields (firstName, lastName, phone, groupId, joinedAt) are required"}), 400

        # Update query
        update_data = {
            "firstName": first_name,
            "lastName": last_name,
            "phone": phone,
            "groupId": group_id,
            "joinedAt": joined_at,
            "age":age
        }

        # Perform the update
        database.volunteers.update_one(
            {"id": volunteer_id},
            {"$set": update_data}
        )

        return jsonify({"message": "Volunteer updated successfully"}), 200

    except Exception as err:
        return jsonify({"error": str(err)}), 500


@volunteers_bp.route('/get-all-volunteers-by-group-id/<string:group_id>', methods=['GET'])
def get_all_volunteers_by_group_id(group_id):
    try:
        # Check if group_id is a valid ObjectId

        # Find the group information (team) from the teams collection
        group = database.teams.find_one({"groupId": group_id})
        if not group:
            return jsonify({"error": "No team found for the given groupId"}), 404

        # Find all volunteers in the volunteers collection by groupId
        volunteers = database.volunteers.find({"groupId": group_id})

        if not volunteers:
            return jsonify({"error": "No volunteers found for the given groupId"}), 404

        transformed_volunteers = []
        for volunteer in volunteers:
            num_of_meetings = int(volunteer.get('numOfMeetings', 0))
            meeting_count = int(group.get('meetingCount', 0))

            # Calculate performance as a percentage
            performance = (num_of_meetings / meeting_count * 100) if meeting_count > 0 else 0

            # Create the transformed volunteer data
            transformed_volunteer = {
                "id": volunteer.get('id'),
                "firstName": volunteer.get('firstName'),
                "lastName": volunteer.get('lastName'),
                "phone": volunteer.get('phone'),
                "age":volunteer.get('age'),
                "joinedAt": volunteer.get('joinedAt'),
                "groupId": volunteer.get('groupId'),
                "group": {
                    "groupId": group["groupId"],
                    "groupName": group["groupName"]
                },
                "performance": performance
            }

            transformed_volunteers.append(transformed_volunteer)

        return jsonify(transformed_volunteers), 200

    except Exception as e:
        # Log the error for debugging
        print(f"Error: {e}")
        return jsonify({"error": f"An error occurred: {e}"}), 500



