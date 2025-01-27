from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
import mysql.connector
import json
from dotenv import load_dotenv
import uuid
from mysql.connector import Error
#app = Flask(__name__)
import os
# Allow CORS only for the /get-all-teams route
#CORS(app, resources={r"/get-all-teams": {"origins": "http://localhost:4500"}})
load_dotenv()
teams_bp = Blueprint('teams', __name__)

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_ROOT'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

@teams_bp.route('/get-all-teams', methods=['GET'])
def get_all_teams():
    try:
        # Open a connection to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # SQL query to get the teams and their volunteers
        cursor.execute("""
        SELECT 
            teams.groupId, 
            teams.groupName, 
            teams.meetingCount,
            teams.status,
            teams.projectName,
            teams.projectInfo,
            teams.dateCreated,
            teams.teamLeaderId,
            CONCAT(team_leader.firstName, ' ', team_leader.lastName) AS teamLeaderName,
            GROUP_CONCAT(
                CONCAT(
                    '{"firstName":"', volunteers.firstName, '",',
                    '"lastName":"', volunteers.lastName, '",',
                    '"phone":"', volunteers.phone, '",',
                    '"joinedAt":"', volunteers.joinedAt, '"}'
                ) SEPARATOR ', '
            ) AS volunteers
        FROM teams
        LEFT JOIN volunteers AS team_leader 
            ON team_leader.id = teams.teamLeaderId  -- This join fetches the team leader details
        LEFT JOIN volunteers 
            ON volunteers.groupId = teams.groupId  -- This join fetches all volunteers for the team
        GROUP BY teams.groupId;
        """)

        # Fetch all the results from the query
        results = cursor.fetchall()

        # Prepare the response data
        team_data = []
        for row in results:
            team = {
                'groupId': row[0],
                'groupName': row[1],
                'meetingCount': row[2],
                'status': row[3],
                'projectName': row[4],
                'projectInfo': row[5],
                'dateCreated': row[6],
                'teamLeader': {
                    'teamLeaderId': row[7],
                    'teamLeaderName': row[8]
                },
                'volunteers': json.loads('[' + row[9] + ']') if row[9] else []  # Handling the volunteers as an object
            }
            team_data.append(team)

        # Close the database connection
        cursor.close()
        connection.close()

        # Return the response as JSON
        return jsonify(team_data)
    
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@teams_bp.route('/create-team', methods=['POST','OPTIONS'])
def create_team():
    if request.method == 'OPTIONS':
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:4500")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.status_code = 200
        return response

    # Get data from the request
    data = request.get_json()
    groupId = str(uuid.uuid4()).replace("-", "")[:12]
    # Validate required fields
    required_fields = ['groupName', 'teamLeaderId', 'dateCreated', 'projectName', 'projectInfo']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
    
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Insert the new volunteer into the database
        insert_query = """
        INSERT INTO teams (groupId,groupName, teamLeaderId, dateCreated, projectName, projectInfo,meetingCount)
        VALUES (%s,%s, %s, %s, %s, %s,%s)
        """
        values = (groupId,data['groupName'], data['teamLeaderId'], data['dateCreated'], data['projectName'], data['projectInfo'],0)
        
        cursor.execute(insert_query, values)
        connection.commit()

        # Return success response

        return jsonify({'message': 'Team created successfully!'}), 200
    except Error as e:
        # Handle database errors
        return jsonify({'error': str(e)}), 500
    finally:
        # Close the database connection
        if connection.is_connected():
            cursor.close()
            connection.close()




@teams_bp.route('/delete-team/<string:team_id>', methods=['DELETE','OPTIONS'])
def delete_team(team_id):
    if request.method == 'OPTIONS':
        # Respond to the preflight request with appropriate headers
        response = jsonify({"message": "CORS preflight successful"})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response, 200
     
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor();
    
    if request.method == 'DELETE':
        try:
            # Execute the DELETE query
            #cursor.execute("DELETE FROM volunteers WHERE id = %s", (team_id,))
            # Delete the team
            cursor.execute("DELETE FROM teams WHERE groupId = %s", (team_id,))
            connection.commit()

            # Check if a row was actually deleted
            if cursor.rowcount == 0:
                return jsonify({'message': 'Team not found'}), 404

            return jsonify({'message': 'Team deleted successfully'}), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

        finally:
            # Clean up resources
            cursor.close()
            connection.close()



@teams_bp.route('/update-team/<string:team_id>', methods=['PUT'])
def update_team(team_id):
    data = request.get_json()
    
    group_name = data.get('groupName')
    team_leader_id = data.get('teamLeaderId')
    date_created = data.get('dateCreated')
    project_name = data.get('projectName')
    project_info = data.get('projectInfo')
    
    try:
        # Open a connection to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Fetch the current teamLeaderId
        cursor.execute("SELECT teamLeaderId FROM teams WHERE groupId = %s", (team_id,))
        old_team_leader_id = cursor.fetchone()
        if not old_team_leader_id:
            return jsonify({'message': 'Team not found'}), 404
        
        old_team_leader_id = old_team_leader_id[0]
        print('old_team_leader_id',old_team_leader_id)
        print('team_leader_id',team_leader_id)


        # Update the teams table
        cursor.execute("""
        UPDATE teams
        SET 
            groupName = %s, 
            teamLeaderId = %s, 
            dateCreated = %s, 
            projectName = %s, 
            projectInfo = %s
        WHERE groupId = %s;
        """, (group_name, team_leader_id, date_created, project_name, project_info, team_id))

        # Commit the changes for the teams table
        connection.commit()

        # Update the users table
        cursor.execute("""
        UPDATE users
        SET id = %s
        WHERE id = %s;
        """, (team_leader_id,old_team_leader_id))

        # Commit the changes for the users table
        connection.commit()

        return jsonify({'message': 'Team and user updated successfully'}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        # Clean up resources
        cursor.close()
        connection.close()



@teams_bp.route('/team/<team_id>', methods=['GET'])
def get_team_by_id(team_id):
    try:
        # Open a connection to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # SQL query to get the team by teamId
        cursor.execute("""
        SELECT 
            teams.groupId, 
            teams.groupName, 
            teams.meetingCount,
            teams.status,
            teams.projectName,
            teams.projectInfo,
            teams.dateCreated,
            teams.teamLeaderId,
            CONCAT(team_leader.firstName, ' ', team_leader.lastName) AS teamLeaderName,
            GROUP_CONCAT(
                CONCAT(
                    '{"firstName":"', volunteers.firstName, '",',
                    '"lastName":"', volunteers.lastName, '",',
                    '"phone":"', volunteers.phone, '",',
                    '"joinedAt":"', volunteers.joinedAt, '"}'
                ) SEPARATOR ', '
            ) AS volunteers
        FROM teams
        LEFT JOIN volunteers AS team_leader 
            ON team_leader.id = teams.teamLeaderId  -- This join fetches the team leader details
        LEFT JOIN volunteers 
            ON volunteers.groupId = teams.groupId  -- This join fetches all volunteers for the team
        WHERE teams.groupId = %s  -- Filter by teamId
        GROUP BY teams.groupId;
        """, (team_id,))

        # Fetch the result
        result = cursor.fetchone()  # We use fetchone since we are expecting one row

        if result:
            team = {
                'groupId': result[0],
                'groupName': result[1],
                'meetingCount': result[2],
                'status': result[3],
                'projectName': result[4],
                'projectInfo': result[5],
                'dateCreated': result[6],
                'teamLeader': {
                    'teamLeaderId': result[7],
                    'teamLeaderName': result[8]
                },
                'volunteers': json.loads('[' + result[9] + ']') if result[9] else []  # Handling the volunteers as an object
            }
            # Close the database connection
            cursor.close()
            connection.close()

            # Return the response as JSON
            return jsonify(team)
        else:
            cursor.close()
            connection.close()
            return jsonify({'error': 'Team not found'}), 404  # Return an error if no team is found

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500





@teams_bp.route('/update-team-status/<team_id>', methods=['PUT'])
def update_team_status(team_id):
    try:
        # Parse the request JSON
        data = request.json
        new_status = data.get('status')  # Expecting {"status": "new_status"} in the request body

        if not new_status:
            return jsonify({'error': 'Status is required'}), 400

        # Open a connection to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # SQL query to update the status
        cursor.execute("""
            UPDATE teams
            SET status = %s
            WHERE groupId = %s
        """, (new_status, team_id))

        # Commit the transaction
        connection.commit()

        # Check if a row was updated
        if cursor.rowcount == 0:
            cursor.close()
            connection.close()
            return jsonify({'error': 'Team not found'}), 404

        # Close the connection
        cursor.close()
        connection.close()

        # Return a success response
        return jsonify({'message': 'Status updated successfully', 'groupId': team_id, 'status': new_status}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500