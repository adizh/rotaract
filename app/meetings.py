from flask import Flask, request, jsonify,Blueprint
import mysql.connector
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv
app = Flask(__name__)
meetings_bp = Blueprint('meetings', __name__)
load_dotenv()
# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_ROOT'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

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
        
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Generate a unique meeting ID
        meeting_id = str(uuid.uuid4()).replace("-", "")[:12]
        
        # Insert the meeting for each volunteer ID
        for volunteer_id in volunteer_ids:
            unique_id = str(uuid.uuid4()).replace("-", "")[:12]
            
            # Insert the meeting into the meetings table
            cursor.execute("""
                INSERT INTO meetings (id, name, meetingInfo, format, dateCreated, volunteerId, groupId, unique_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (meeting_id, name, meeting_info, format, date_created, volunteer_id, groupId, unique_id))
            
            # Increment the numOfMeetings for the volunteer, handling NULL values
            cursor.execute("""
                UPDATE volunteers 
                SET numOfMeetings = numOfMeetings + 1
                WHERE id = %s
            """, (volunteer_id,))

        # Increment the meetingCount for the team (groupId), handling NULL values
        cursor.execute("""
            UPDATE teams 
            SET meetingCount = meetingCount + 1
            WHERE groupId = %s
        """, (groupId,))

        # Commit the transaction
        connection.commit()

        # Close the database connection
        cursor.close()
        connection.close()

        return jsonify({'message': 'Meeting created successfully for all volunteers!'}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@meetings_bp.route('/fetch-all-meetings', methods=['GET'])
def fetch_all_meetings():
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # SQL query to fetch meetings with volunteers and team leader info
        cursor.execute("""
            SELECT 
                m.id, 
                m.unique_id,
                m.name, 
                m.groupId, 
                m.format, 
                m.meetingInfo, 
                m.dateCreated,
                v.firstName AS volunteerFirstName,
                v.lastName AS volunteerLastName,
                v.id AS volunteerId,
                tl.firstName AS teamLeaderFirstName,
                tl.lastName AS teamLeaderLastName,
                tl.id AS teamLeaderId
            FROM 
                meetings m
            LEFT JOIN 
                volunteers v ON m.volunteerId = v.id
            LEFT JOIN 
                teams t ON m.groupId = t.groupId
            LEFT JOIN 
                volunteers tl ON t.teamLeaderId = tl.id
        """)

        # Fetch all rows
        rows = cursor.fetchall()

        # Group results by meeting ID
        meetings = {}
        for row in rows:
            meeting_id = row[0]
            if meeting_id not in meetings:
                # Initialize meeting structure if not already added
                meetings[meeting_id] = {
                    'id': row[0],
                    'unique_id': row[1],
                    'name': row[2],
                    'groupId': row[3],
                    'format': row[4],
                    'meetingInfo': row[5],
                    'dateCreated': row[6],
                    'volunteers': [],
                    'teamLeader': {
                        'firstName': row[10],
                        'lastName': row[11],
                        'teamLeaderId': row[12]
                    }
                }

            # Append volunteer information for this meeting
            if row[7] and row[8] and row[9]:  # Check if volunteer info exists
                meetings[meeting_id]['volunteers'].append({
                    'firstName': row[7],
                    'lastName': row[8],
                    'volunteerId': row[9]
                })

        # Close the database connection
        cursor.close()
        connection.close()

        # Convert meetings dictionary to a list
        return jsonify({'meetings': list(meetings.values())}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    





@meetings_bp.route('/delete-meeting/<string:meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Check if the meeting exists
        cursor.execute("SELECT id FROM meetings WHERE id = %s", (meeting_id,))
        meeting = cursor.fetchone()
        
        # If meeting doesn't exist
        if not meeting:
            return jsonify({'error': 'Meeting not found'}), 404

        # Ensure no unread results exist
        cursor.fetchall()  # Read any remaining result sets

        # Delete the meeting
        cursor.execute("DELETE FROM meetings WHERE id = %s", (meeting_id,))
        connection.commit()

        # Close the database connection
        cursor.close()
        connection.close()

        return jsonify({'message': 'Meeting deleted successfully'}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        


@meetings_bp.route('/fetch-all-meetings-groupId/<group_id>', methods=['GET'])
def fetch_all_meetings_by_groupId(group_id):
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # SQL query to fetch meetings with volunteers and team leader info, filtered by groupId
        cursor.execute("""
            SELECT 
                m.id, 
                m.unique_id,
                m.name, 
                m.groupId, 
                m.format, 
                m.meetingInfo, 
                m.dateCreated,
                v.firstName AS volunteerFirstName,
                v.lastName AS volunteerLastName,
                v.id AS volunteerId,
                tl.firstName AS teamLeaderFirstName,
                tl.lastName AS teamLeaderLastName,
                tl.id AS teamLeaderId
            FROM 
                meetings m
            LEFT JOIN 
                volunteers v ON m.volunteerId = v.id
            LEFT JOIN 
                teams t ON m.groupId = t.groupId
            LEFT JOIN 
                volunteers tl ON t.teamLeaderId = tl.id
            WHERE 
                m.groupId = %s
        """, (group_id,))

        # Fetch all rows
        rows = cursor.fetchall()

        # Group results by meeting ID
        meetings = {}
        for row in rows:
            meeting_id = row[0]
            if meeting_id not in meetings:
                # Initialize meeting structure if not already added
                meetings[meeting_id] = {
                    'id': row[0],
                    'unique_id': row[1],
                    'name': row[2],
                    'groupId': row[3],
                    'format': row[4],
                    'meetingInfo': row[5],
                    'dateCreated': row[6],
                    'volunteers': [],
                    'teamLeader': {
                        'firstName': row[10],
                        'lastName': row[11],
                        'teamLeaderId': row[12]
                    }
                }

            # Append volunteer information for this meeting
            if row[7] and row[8] and row[9]:  # Check if volunteer info exists
                meetings[meeting_id]['volunteers'].append({
                    'firstName': row[7],
                    'lastName': row[8],
                    'volunteerId': row[9]
                })

        # Close the database connection
        cursor.close()
        connection.close()

        # Convert meetings dictionary to a list and return
        return jsonify({'meetings': list(meetings.values())}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
