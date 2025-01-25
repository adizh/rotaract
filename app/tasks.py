from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
import mysql.connector
import json
import uuid
from mysql.connector import Error
import logging
import os
#app = Flask(__name__)

# Allow CORS only for the /get-all-teams route
#CORS(app, resources={r"/get-all-teams": {"origins": "http://localhost:4500"}})

tasks_bp = Blueprint('tasks', __name__)

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_ROOT'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}
@tasks_bp.route('/create-task', methods=['POST'])
def create_task():
    try:
        # Get data from the request
        data = request.json
        
        name = data.get('name')  # Task name
        group_id = data.get('groupId')  # Group ID (12-character string)
        volunteer_ids = data.get('volunteerId')  # List of Volunteer IDs
        is_done = data.get('isDone')  # Task status, default to 0 (false)
        date_created = data.get('dateCreated')  # Optional date, defaults to current timestamp

        # Validate input
        if not all([ name, group_id, volunteer_ids]) or not isinstance(volunteer_ids, list):
            return jsonify({'error': 'Missing required fields or invalid volunteerId format'}), 400

        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        task_id = str(uuid.uuid4()).replace("-", "")[:12]

        # Insert the task for each volunteer ID
        for volunteer_id in volunteer_ids:
            
            cursor.execute("""
                INSERT INTO tasks (id, name, groupId, volunteerId, isDone, dateCreated)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (task_id, name, group_id, volunteer_id, is_done, date_created))

        # Commit the transaction
        connection.commit()

        # Close the database connection
        cursor.close()
        connection.close()

        return jsonify({'message': 'Task created successfully for all volunteers!'}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500





@tasks_bp.route('/get-all-tasks', methods=['GET'])
def get_all_tasks():
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)  # Use dictionary=True for better readability

        # SQL query to fetch tasks and group by name, along with volunteer details
        query = """
        SELECT 
            t.name, 
            t.groupId, 
            t.isDone, 
            t.dateCreated, 
            t.id AS taskId,
            v.id AS volunteerId,
            v.firstName AS firstName,
            v.lastName AS lastName
        FROM tasks AS t
        LEFT JOIN volunteers AS v ON t.volunteerId = v.id
        ORDER BY t.name, t.groupId;
        """
        cursor.execute(query)

        # Fetch results
        tasks = cursor.fetchall()

        # Prepare the final result in the desired format
        task_map = {}
        for task in tasks:
            task_name = task['name']
            if task_name not in task_map:
                task_map[task_name] = {
                    'name': task_name,
                    'groupId': task['groupId'],
                    'isDone': bool(task['isDone']),
                    'dateCreated': task['dateCreated'],
                    'id': task['taskId'],
                    'volunteers': []
                }
            # Add the volunteer info to the corresponding task
            task_map[task_name]['volunteers'].append({
                'firstName': task['firstName'],
                'lastName': task['lastName'],
                'volunteerId': task['volunteerId']
            })

        # Convert the task_map to a list
        result = list(task_map.values())

        # Close the database connection
        cursor.close()
        connection.close()

        return jsonify(result), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    



@tasks_bp.route('/get-tasks-by-group/<group_id>', methods=['GET'])
def get_tasks_by_group(group_id):
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)  # Use dictionary=True for better readability

        # SQL query to fetch tasks for the given groupId, along with volunteer details
        query = """
        SELECT 
            t.name, 
            t.groupId, 
            t.isDone, 
            t.dateCreated, 
            t.id AS taskId,
            v.id AS volunteerId,
            v.firstName AS firstName,
            v.lastName AS lastName
        FROM tasks AS t
        LEFT JOIN volunteers AS v ON t.volunteerId = v.id
        WHERE t.groupId = %s
        ORDER BY t.name;
        """
        cursor.execute(query, (group_id,))

        # Fetch results
        tasks = cursor.fetchall()

        # Prepare the final result in the desired format
        task_map = {}
        for task in tasks:
            task_name = task['name']
            if task_name not in task_map:
                task_map[task_name] = {
                    'name': task_name,
                    'groupId': task['groupId'],
                    'isDone': bool(task['isDone']),
                    'dateCreated': task['dateCreated'],
                    'id': task['taskId'],
                    'volunteers': []
                }
            # Add the volunteer info to the corresponding task
            task_map[task_name]['volunteers'].append({
                'firstName': task['firstName'],
                'lastName': task['lastName'],
                'volunteerId': task['volunteerId']
            })

        # Convert the task_map to a list
        result = list(task_map.values())

        # Close the database connection
        cursor.close()
        connection.close()

        return jsonify(result), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    








@tasks_bp.route('/delete-task/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Check if the task exists
        cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
        task = cursor.fetchone()

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        # Consume the result properly
        cursor.fetchall()  # This consumes the result to avoid "Unread result found"

        # Now delete all tasks with the same id (since id is not unique)
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        connection.commit()

        return jsonify({'message': 'Task(s) deleted successfully'}), 200
    except mysql.connector.Error as e:
        # Log the full error for debugging purposes
        logging.error(f"Error during task deletion: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        # Catch any other exceptions and log them
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@tasks_bp.route('/update-task/<task_id>', methods=['PUT'])
def update_task(task_id):
    try:
        # Get data from the request body
        data = request.json

        # Extract fields from the request body
        name = data.get('name')
        volunteer_ids = data.get('volunteerId')
        is_done = data.get('isDone')
        date_created = data.get('dateCreated')
        group_id = data.get('groupId')  # Assuming you also need groupId in the request

        # Validate the input
        if not name or not isinstance(name, str):
            return jsonify({'error': 'Invalid or missing task name'}), 400
        if not isinstance(volunteer_ids, list):
            return jsonify({'error': 'Invalid volunteer IDs'}), 400
        if not all(isinstance(v, str) and len(v) == 12 for v in volunteer_ids):  # Ensure each volunteerId is a valid 12-char string
            return jsonify({'error': 'All volunteerIds must be 12 characters long'}), 400

        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Check if the task exists
        cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
        task = cursor.fetchone()

        # Make sure the result is consumed before proceeding (even if it's just one result)
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        # Clear any pending results to avoid unread result errors
        cursor.fetchall()  # This ensures the result is fully consumed

        # Remove old volunteer associations for this task (if necessary)
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))

        # Insert new volunteer associations
        for volunteer_id in volunteer_ids:
            cursor.execute("""
                INSERT INTO tasks (id, name, groupId, volunteerId, isDone, dateCreated)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (task_id, name, group_id, volunteer_id, is_done, date_created))

        # Commit the transaction
        connection.commit()

        # Close the database connection properly
        cursor.close()
        connection.close()

        return jsonify({'message': 'Task updated successfully for all volunteers!'}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
