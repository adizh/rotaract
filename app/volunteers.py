from flask import Blueprint, request, jsonify
import mysql.connector
import uuid
from mysql.connector import Error
import os
# Create a blueprint for volunteers
volunteers_bp = Blueprint('volunteers', __name__)
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_ROOT'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

@volunteers_bp.route('/get-volunteer-by-id/<int:volunteer_id>', methods=['GET'])
def get_volunteer_by_id(volunteer_id):
    try:
        # Open a connection to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # SQL query to get volunteer by ID
        cursor.execute("""
            SELECT 
                id,
                firstName,
                lastName,
                phone,
                joinedAt,
                groupId,
                numOfMeetings
            FROM volunteers
            WHERE id = %s
        """, (volunteer_id,))

        # Fetch the result from the query
        result = cursor.fetchone()

        if result:
            # Prepare the response data
            volunteer = {
                'id': result[0],
                'firstName': result[1],
                'lastName': result[2],
                'phone': result[3],
                'joinedAt': result[4],
                'groupId': result[5],
                'numOfMeetings': result[6],
            }

            # Close the database connection
            cursor.close()
            connection.close()

            return jsonify(volunteer)  # Return the volunteer data as JSON

        else:
            # If no volunteer is found with that ID
            return jsonify({'error': 'Volunteer not found'}), 404

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500



@volunteers_bp.route('/get-all', methods=['GET'])
def get_all_volunteers():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)

        # Use a JOIN to fetch groupName from the teams table
        query = """
        SELECT 
            v.id, 
            v.firstName, 
            v.lastName, 
            v.phone, 
            v.joinedAt, 
            v.groupId, 
            t.groupName AS groupName,
            t.numOfMeetings
        FROM 
            volunteers v
        LEFT JOIN 
            teams t 
        ON 
            v.groupId = t.groupId
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        # Transform the data to replace groupId with group object
        transformed_rows = [
            {
                **row,
                "group": {
                    "groupId": row["groupId"],
                    "groupName": row["groupName"]
                }
            }
            for row in rows
        ]
        
        # Remove old groupId and groupName from the top level
        for row in transformed_rows:
            del row["groupId"]
            del row["groupName"]

        cursor.close()
        connection.close()

        return jsonify(transformed_rows)

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    

@volunteers_bp.route('/delete-volunteer/<string:volunteer_id>', methods=['DELETE'])
def delete_volunteer(volunteer_id):
    try:
        # Open a connection to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # SQL query to set volunteerId to NULL in tasks table
        cursor.execute("""
            DELETE FROM tasks 
            WHERE volunteerId = %s
        """, (volunteer_id,))

        # Now, delete the volunteer from the volunteers table
        cursor.execute("""
            DELETE FROM volunteers 
            WHERE id = %s
        """, (volunteer_id,))

        # Commit the changes
        connection.commit()

        # Check if a row was affected (meaning the volunteer was deleted)
        if cursor.rowcount > 0:
            return jsonify({'message': 'Volunteer and associated tasks updated successfully'}), 200
        else:
            return jsonify({'message': 'Volunteer not found'}), 404
        
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        # Clean up resources
        cursor.close()
        connection.close()






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

    # Validate the received data (you can add more validation as needed)
    if not first_name or not last_name or not phone or not group_id:
        return jsonify({'error': 'Missing required fields'}), 400




    try:
        # Open a connection to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()


        # SQL query to insert the new volunteer
        cursor.execute("""
            INSERT INTO volunteers (id,firstName, lastName, phone, joinedAt, groupId,numOfMeetings)
            VALUES (%s,%s, %s, %s, %s, %s,%s)
        """, (id,first_name, last_name, phone, joined_at, group_id,0))

        # Commit the transaction
        connection.commit()

        # Return a success message
        return jsonify({'message': 'Volunteer created successfully'}), 200

    except mysql.connector.Error as err:
        # Return an error message in case of an issue with the database
        return jsonify({'error': str(err)}), 500

    finally:
        # Close the database connection
        cursor.close()
        connection.close()






@volunteers_bp.route('/update-volunteer/<string:volunteer_id>', methods=['PUT'])
def update_volunteer(volunteer_id):
    try:
        # Get the request data (assuming JSON)
        data = request.get_json()

        # Extract the data you need to update
        first_name = data.get('firstName')
        last_name = data.get('lastName')
        phone = data.get('phone')
        group_id = data.get('groupId')
        joinedAt = data.get('joinedAt')

        # Validate input data
        if not first_name or not last_name or not phone or not group_id or not joinedAt:
            return jsonify({"error": "All fields (firstName, lastName, phone, groupId) are required"}), 400

        # Open a connection to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # SQL query to update the volunteer information
        update_query = """
            UPDATE volunteers
            SET firstName = %s, lastName = %s, phone = %s, groupId = %s, joinedAt=%s
            WHERE id = %s
        """
        
        # Execute the query
        cursor.execute(update_query, (first_name, last_name, phone, group_id, joinedAt,volunteer_id))
        connection.commit()

        # Check if any row was updated
        if cursor.rowcount == 0:
            return jsonify({"error": "Volunteer not found"}), 404

        # Close the cursor and connection
        cursor.close()
        connection.close()

        # Return success response
        return jsonify({"message": "Volunteer updated successfully"}), 200

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


@volunteers_bp.route('/get-all-volunteers-by-group-id/<string:group_id>', methods=['GET'])
def get_all_volunteers_by_group_id(group_id):
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)

        # Execute the query
        with connection.cursor(dictionary=True) as cursor:
            query = """
                SELECT 
                    v.id, 
                    v.firstName, 
                    v.lastName, 
                    v.phone, 
                    v.joinedAt, 
                    v.groupId, 
                    t.groupName AS groupName,
                    v.numOfMeetings,
                    t.meetingCount
                FROM 
                    volunteers v
                LEFT JOIN 
                    teams t 
                ON 
                    v.groupId = t.groupId
                WHERE 
                    v.groupId = %s
            """
            cursor.execute(query, (group_id,))
            rows = cursor.fetchall()

            if not rows:
                return jsonify({"error": "No volunteers found for the given groupId"}), 404

            # Transform the data to add performance field
            transformed_rows = []
            for row in rows:
                # Calculate performance as a percentage
                num_of_meetings = int(row['numOfMeetings'] or 0)
                meeting_count = int(row['meetingCount'] or 0)
                
                # Calculate performance as a percentage
                performance = (num_of_meetings / meeting_count * 100) if meeting_count > 0 else 0

                # Append the row with calculated performance
                transformed_row = {
                    **row,
                    "group": {
                        "groupId": row["groupId"],
                        "groupName": row["groupName"]
                    },
                    "performance": performance  # Add performance calculation
                }

                # Remove old groupId and groupName from the top level
                del transformed_row["groupId"]
                del transformed_row["groupName"]
                
                transformed_rows.append(transformed_row)

            # Return the transformed rows
            return jsonify(transformed_rows)

    except mysql.connector.Error as err:
        # Log the error for debugging
        print(f"Database error: {err}")
        return jsonify({"error": f"Database query failed: {err}"}), 500

    except Exception as e:
        # Log any other exceptions
        print(f"Error: {e}")
        return jsonify({"error": f"An error occurred: {e}"}), 500

    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()

