from flask import Flask, request, jsonify,Blueprint
import mysql.connector
import uuid
from datetime import datetime
import os
import traceback
from dotenv import load_dotenv
app = Flask(__name__)
from flask_cors import CORS
from pymongo import MongoClient
meetings_bp = Blueprint('meetings', __name__)
load_dotenv()
# Database configuration
client = MongoClient(os.getenv('CONNECTION_STRING'))
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:4500", "https://rotaract-front-17bdmy7ft-adizhs-projects.vercel.app"]}}) 
database = client.rotaract

@meetings_bp.route('/create-meeting/<groupId>', methods=['POST'])
def create_meeting(groupId):
    try:
        # Get data from the request
        data = request.json
        name = data.get('name')  # Meeting name
        volunteer_ids = data.get('volunteerId')  # List of Volunteer IDs
        meeting_info = data.get('meetingInfo')  # Meeting info
        format = data.get('format')  # Meeting format
        date_created = data.get('dateCreated', datetime.now().strftime('%Y-%m-%d'))  # Optional date, default to current date

        # Validate input
        if not all([name, volunteer_ids]) or not isinstance(volunteer_ids, list):
            return jsonify({'error': 'Missing required fields or invalid volunteerId format'}), 400

        # Generate a unique meeting ID
        meeting_id = str(uuid.uuid4()).replace("-", "")[:12]
        
        # Prepare meeting data for insertion
        meeting_data = {
            "id": meeting_id,
            "name": name,
            "meetingInfo": meeting_info,
            "format": format,
            "dateCreated": date_created,
            "volunteerId": volunteer_ids,  # List of volunteer IDs for this meeting
            "groupId": groupId
        }

        # Insert the meeting into the meetings collection
        meeting_result = database.meetings.insert_one(meeting_data)

        # Update the volunteer collection to increment the number of meetings
        for volunteer_id in volunteer_ids:
            database.volunteers.update_one(
                {"id": volunteer_id}, 
                {"$inc": {"numOfMeetings": 1}}  # Increment numOfMeetings by 1
            )

        # Increment the meeting count for the team (groupId)
        database.teams.update_one(
        {"groupId": groupId}, 
        {"$inc": {"meetingCount": 1}}
)
   
        


        return jsonify({'message': 'Meeting created successfully for all volunteers!'}), 200

    except Exception as e:
        # Log the error for debugging
       
        return jsonify({'error': str(e)}), 500



from bson import ObjectId





from .verify_token import verify_token

@meetings_bp.route('/fetch-all-meetings', methods=['GET'])

def fetch_all_meetings():
    decoded_token = verify_token()
    if decoded_token is None:
         return jsonify({'error': 'Token is invalid or expired'}), 401
    try:
        pipeline = [
            # 1. Lookup teams collection to get groupName and teamLeaderId
            {
                "$lookup": {
                    "from": "teams",
                    "localField": "groupId",
                    "foreignField": "groupId",
                    "as": "teamDetails"
                }
            },
            {
                "$unwind": {
                    "path": "$teamDetails",
                    "preserveNullAndEmptyArrays": True
                }
            },

            # 2. Lookup volunteers collection to get teamLeader details
            {
                "$lookup": {
                    "from": "volunteers",
                    "localField": "teamDetails.teamLeaderId",
                    "foreignField": "id",
                    "as": "teamLeaderDetails"
                }
            },
            {
                "$unwind": {
                    "path": "$teamLeaderDetails",
                    "preserveNullAndEmptyArrays": True
                }
            },

            # 3. Lookup volunteers for volunteerId (transform array of IDs into objects)
            {
                "$lookup": {
                    "from": "volunteers",
                    "localField": "volunteerId",
                    "foreignField": "id",
                    "as": "volunteerDetails"
                }
            },

            # 4. Remove unnecessary fields before grouping
            {
                "$project": {
                    "groupId": 1,
                    "groupName": "$teamDetails.groupName",
                    "teamLeaderId": "$teamDetails.teamLeaderId",
                    "firstName": "$teamLeaderDetails.firstName",
                    "lastName": "$teamLeaderDetails.lastName",
                    "meetingId": "$_id",
                    "id": 1,
                    "name": 1,
                    "meetingInfo": 1,
                    "format": 1,
                    "dateCreated": 1,
                    "groupId": 1,

                    # Transform volunteerId into objects
                    "volunteers": {
                        "$map": {
                            "input": "$volunteerDetails",
                            "as": "vol",
                            "in": {
                                "volunteerId": "$$vol.id",
                                "firstName": "$$vol.firstName",
                                "lastName": "$$vol.lastName"
                            }
                        }
                    }
                }
            },

            # 5. Group by groupId
            {
                "$group": {
                    "_id": "$groupId",
                    "groupId": { "$first": "$groupId" },
                    "groupName": { "$first": "$groupName" },
                    "teamLeader": {
                        "$first": {
                            "teamLeaderId": "$teamLeaderId",
                            "firstName": "$firstName",
                            "lastName": "$lastName"
                        }
                    },
                    "meetings": { 
                        "$push": {
                            "meetingId": "$meetingId",
                            "id": "$id",
                            "name": "$name",
                            "meetingInfo": "$meetingInfo",
                            "format": "$format",
                            "dateCreated": "$dateCreated",
                            "volunteers": "$volunteers",
                            "groupId": "$groupId"
                        }
                    }
                }
            },

            # 6. Final Projection
            {
                "$project": {
                    "_id": 1,
                    "groupId": 1,
                    "groupName": 1,
                    "teamLeader": 1,
                    "meetings": 1
                }
            }
        ]

        grouped_meetings = list(database.meetings.aggregate(pipeline))

        # Convert ObjectId fields to strings
        def convert_objectid(obj):
            """ Recursively convert ObjectId fields to strings in dictionaries/lists """
            if isinstance(obj, dict):
                return {k: convert_objectid(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_objectid(i) for i in obj]
            elif isinstance(obj, ObjectId):
                return str(obj)
            return obj

        grouped_meetings = convert_objectid(grouped_meetings)

        return jsonify({'meetings': grouped_meetings}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500









@meetings_bp.route('/delete-meeting/<string:meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    try:
        # Validate ObjectId


        # Check if the meeting exists
        meeting = database.meetings.find_one({"id": meeting_id})
        
        if not meeting:
            return jsonify({'error': 'Meeting not found'}), 404

        # Delete the meeting
        result = database.meetings.delete_one({"id": meeting_id})
        
        if result.deleted_count == 0:
            return jsonify({'error': 'Failed to delete meeting'}), 500

        return jsonify({'message': 'Meeting deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@meetings_bp.route('/fetch-all-meetings-groupId/<group_id>', methods=['GET'])
def fetch_all_meetings_by_groupId(group_id):
    try:
        # MongoDB aggregation pipeline
        pipeline = [
            {"$match": {"groupId": group_id}},

            # Lookup volunteers (volunteerId -> volunteers)
            {
                "$lookup": {
                    "from": "volunteers",
                    "localField": "volunteerId",
                    "foreignField": "id",
                    "as": "volunteers"
                }
            },

            # Lookup teams (groupId -> teams)
            {
                "$lookup": {
                    "from": "teams",
                    "localField": "groupId",
                    "foreignField": "groupId",
                    "as": "team"
                }
            },

            {"$unwind": "$team"},  # Extract team object

            # Lookup team leader info (team.teamLeaderId -> volunteers)
            {
                "$lookup": {
                    "from": "volunteers",
                    "localField": "team.teamLeaderId",
                    "foreignField": "id",
                    "as": "teamLeader"
                }
            },

            {"$unwind": "$teamLeader"},  # Extract team leader object

            # Format the final output
            {
                "$project": {
                    "_id": 0,
                    "id": "$id",
                    "name": "$name",
                    "groupId": "$groupId",
                    "format": "$format",
                    "meetingInfo": "$meetingInfo",
                    "dateCreated": "$dateCreated",

                    # Collect volunteers as an array of objects
                    "volunteers": {
                        "$map": {
                            "input": "$volunteers",
                            "as": "volunteer",
                            "in": {
                                "firstName": "$$volunteer.firstName",
                                "lastName": "$$volunteer.lastName",
                                "volunteerId": "$$volunteer.id"
                            }
                        }
                    },

                    # Keep teamLeader as a single object
                    "teamLeader": {
                        "firstName": "$teamLeader.firstName",
                        "lastName": "$teamLeader.lastName",
                        "teamLeaderId": "$teamLeader.id"
                    }
                }
            }
        ]

        # Execute aggregation
        meetings = list(database.meetings.aggregate(pipeline))

        # Return response
        return jsonify({'meetings': meetings}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
