from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
import mysql.connector
import json
from flask_cors import CORS
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv
import uuid
from .verify_token import verify_token
from mysql.connector import Error
app = Flask(__name__)
import os
CORS(app, resources={r"/*": {"origins": ["http://localhost:4500", "https://rotaract-front-17bdmy7ft-adizhs-projects.vercel.app","https://scintillating-dasik-a1e6aa.netlify.app"]}}) 
load_dotenv()
teams_bp = Blueprint('teams', __name__)
client = MongoClient(os.getenv('CONNECTION_STRING'))

database = client.rotaract
def convert_objectid_to_string(doc):
    """Convert ObjectId fields to string in a document"""
    if isinstance(doc, dict):
        return {key: (str(value) if isinstance(value, ObjectId) else value) for key, value in doc.items()}
    return doc

def convert_objectid_to_strings(data):
    """Recursively convert all ObjectId instances to string."""
    if isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, dict):
        return {key: convert_objectid_to_strings(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_objectid_to_strings(item) for item in data]
    return data

@teams_bp.route('/get-all-teams', methods=['GET'])
def get_all_teams():
    decoded_token = verify_token()
    if decoded_token is None:
         return jsonify({'error': 'Token is invalid or expired'}), 401
    
    try:
        
        # Retrieve all teams
        teams = list(database.teams.find())

        # Process each team to add the teamLeader and volunteers info
        for team in teams:
            # Get the team leader information using the teamLeaderId
            team_leader = database.volunteers.find_one({"id": team.get("teamLeaderId")})

            if team_leader:
                # Combine firstName and lastName to form the team leader name
                team['teamLeader'] = {
                    "teamLeaderId": team.get("teamLeaderId"),
                    "teamLeaderName": f"{team_leader.get('firstName')} {team_leader.get('lastName')}"
                }
            else:
                team['teamLeader'] = {
                    "teamLeaderId": team.get("teamLeaderId"),
                    "teamLeaderName": "Unknown"
                }

            # Get volunteers who have the same groupId as the team's groupId
            group_id = team.get('groupId')
            volunteers = list(database.volunteers.find({"groupId": group_id}))

            # Add all volunteer data to the 'volunteers' field
            team['volunteers'] = [volunteer for volunteer in volunteers]

        # Convert ObjectId to string for serialization
        teams = convert_objectid_to_strings(teams)

        return jsonify(teams)

    except Exception as err:
        return jsonify({'error': str(err)}), 500




   


@teams_bp.route('/create-team', methods=['POST', 'OPTIONS'])
def create_team():
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'CORS preflight successful'})
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response, 200
    # Handle OPTIONS request for CORS pre-flight

    # Get data from the request
    data = request.get_json()

    # Validate required fields
    required_fields = ['groupName', 'teamLeaderId', 'dateCreated', 'projectName', 'projectInfo']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

    # Generate a unique groupId (UUID-like string)
    group_id = str(uuid.uuid4()).replace("-", "")[:12]

    # Prepare the new team data
    team_data = {
        "groupId": group_id,
        "groupName": data['groupName'],
        "teamLeaderId": data['teamLeaderId'],
        "dateCreated": data['dateCreated'],
        "projectName": data['projectName'],
        "projectInfo": data['projectInfo'],
        "meetingCount": 0,
        "status": '1'
    }

    try:
        # Insert the new team into the MongoDB collection
        result = database.teams.insert_one(team_data)

        if result.inserted_id:
            # Assign the same groupId to the team leader in the volunteers collection
            volunteers_result = database.volunteers.update_one(
                {'volunteerId': data['teamLeaderId']},  # Find the team leader
                {'$set': {'groupId': group_id}}  # Assign the same groupId
            )

            # Check if the volunteer was updated
            if volunteers_result.matched_count > 0:
                return jsonify({'message': 'Team created successfully and team leader assigned!'}), 200
            else:
                return jsonify({'message': 'Team created, but team leader not found in volunteers collection'}), 200

        else:
            return jsonify({'error': 'Failed to create team'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@teams_bp.route('/delete-team/<string:team_id>', methods=['DELETE', 'OPTIONS'])
def delete_team(team_id):
    if request.method == 'OPTIONS':
        response = jsonify({"message": "CORS preflight successful"})
        response.headers['Access-Control-Allow-Methods'] = 'DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response, 200

    if request.method == 'DELETE':
        try:
            # Delete the team
            team_result = database.teams.delete_one({'groupId': team_id})

            if team_result.deleted_count == 0:
                return jsonify({'message': 'Team not found'}), 404

            # Delete all meetings associated with the team
            meetings_result = database.meetings.delete_many({'groupId': team_id})

            # Update volunteers collection by setting groupId to an empty string
            volunteers_result = database.volunteers.update_many(
                {'groupId': team_id},
                {'$set': {'groupId': ''}}
            )

            message = "Team deleted successfully"
            if meetings_result.deleted_count > 0:
                message += f", {meetings_result.deleted_count} meetings deleted"
            if volunteers_result.modified_count > 0:
                message += f", {volunteers_result.modified_count} volunteers updated"

            return jsonify({'message': message}), 200

        except Exception as e:
            app.logger.error(f"Error deleting team {team_id}: {str(e)}")  # Log error
            return jsonify({'error': 'An internal error occurred'}), 500



@teams_bp.route('/update-team/<string:team_id>', methods=['PUT'])
def update_team(team_id):
    data = request.get_json()
    
    group_name = data.get('groupName')
    team_leader_id = data.get('teamLeaderId')
    date_created = data.get('dateCreated')
    project_name = data.get('projectName')
    project_info = data.get('projectInfo')

    try:


        # Fetch the current team leader's id from the team document
        team = database.teams.find_one({'groupId': team_id})
        if not team:
            return jsonify({'message': 'Team not found'}), 404

        old_team_leader_id = team.get('teamLeaderId')
        print('Old team leader id:', old_team_leader_id)
        print('New team leader id:', team_leader_id)

        # Update the teams collection
        result = database.teams.update_one(
            {'groupId': team_id},  # Filter by team_id
            {
                '$set': {
                    'groupName': group_name,
                    'teamLeaderId': team_leader_id,
                    'dateCreated': date_created,
                    'projectName': project_name,
                    'projectInfo': project_info
                }
            }
        )

        if result.modified_count == 0:
            return jsonify({'message': 'No changes made to the team'}), 400

        # If team leader id has changed, update the users collection
        # if old_team_leader_id != team_leader_id:
        #     users_collection.update_one(
        #         {'_id': ObjectId(old_team_leader_id)},  # Filter by old team leader id
        #         {'$set': {'id': team_leader_id}}  # Update the team leader id in the users collection
        #     )

        return jsonify({'message': 'Team and user updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@teams_bp.route('/team/<team_id>', methods=['GET'])
def get_team_by_id(team_id):
    try:
        # MongoDB aggregation pipeline
        pipeline = [
            {
                "$match": {"groupId": team_id}  # Match the team by groupId
            },
            {
                "$lookup": {
                    "from": "volunteers",  # Join with the volunteers collection
                    "localField": "teamLeaderId",  # Match the team leader ID
                    "foreignField": "id",  # Match the volunteer ID
                    "as": "teamLeader"  # Alias for the team leader data
                }
            },
            {
                "$unwind": "$teamLeader"  # Unwind the teamLeader array (we expect only one leader)
            },
            {
                "$lookup": {
                    "from": "volunteers",  # Join with the volunteers collection again for the rest of the volunteers
                    "localField": "groupId",  # Match the groupId for all volunteers in the team
                    "foreignField": "groupId",  # Match volunteers by groupId
                    "as": "volunteers"  # Alias for the volunteers data
                }
            },
            {
                "$project": {  # Project the required fields
                    "_id": 0,  # Exclude the _id field
                    "groupId": 1,
                    "groupName": 1,
                    "meetingCount": 1,
                    "status": 1,
                    "projectName": 1,
                    "projectInfo": 1,
                    "dateCreated": 1,
                    "teamLeader": {
                        "teamLeaderId": "$teamLeader.id",  # Extract the team leader's ID
                        "teamLeaderName": {
                            "$concat": ["$teamLeader.firstName", " ", "$teamLeader.lastName"]  # Combine first and last name
                        }
                    },
                    "volunteers": {

                        "$map": {
                            "input": "$volunteers",  # Map through all volunteers
                            "as": "volunteer",
                            "in": {
                                "firstName": "$$volunteer.firstName",
                                "lastName": "$$volunteer.lastName",
                                "phone": "$$volunteer.phone",
                                "joinedAt": "$$volunteer.joinedAt"
                            }
                        }
                    }
                }
            }
        ]

        # Execute the aggregation pipeline
        result = list(database.teams.aggregate(pipeline))

        if result:
            team = result[0]  # Since we are expecting a single result, take the first document
            return jsonify(team)
        else:
            return jsonify({'error': 'Team not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500





@teams_bp.route('/update-team-status/<team_id>', methods=['PUT'])
def update_team_status(team_id):
    try:
        # Parse the request JSON
        data = request.json
        new_status = data.get('status')  # Expecting {"status": "new_status"} in the request body

        if not new_status:
            return jsonify({'error': 'Status is required'}), 400

        # Update the team's status in the MongoDB database
        result = database.teams.update_one(
            {"groupId": team_id},  # Find the team by groupId
            {"$set": {"status": new_status}}  # Set the new status
        )

        # Check if any document was modified
        if result.matched_count == 0:
            return jsonify({'error': 'Team not found'}), 404

        # Return a success response
        return jsonify({'message': 'Status updated successfully', 'groupId': team_id, 'status': new_status}), 200

    except Exception as e:
        # Log the error for debugging
       
        return jsonify({'error': 'An error occurred'}), 500
