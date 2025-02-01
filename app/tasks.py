from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
import mysql.connector
import json
import uuid
from mysql.connector import Error
from pymongo import MongoClient
from mysql.connector import Error
from bson import ObjectId
import logging
import os
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:4500"}}) 
#app = Flask(__name__)

# Allow CORS only for the /get-all-teams route
#CORS(app, resources={r"/get-all-teams": {"origins": "http://localhost:4500"}})

tasks_bp = Blueprint('tasks', __name__)

volunteers_bp = Blueprint('volunteers', __name__)
client = MongoClient(os.getenv('CONNECTION_STRING'))

database = client.rotaract
task_id = str(uuid.uuid4()).replace("-", "")[:12]

@tasks_bp.route('/create-task', methods=['POST'])
def create_task():
    try:
        # Get data from the request
        data = request.json

        name = data.get('name')  # Task name
        group_id = data.get('groupId')  # Group ID (12-character string)
        volunteer_ids = data.get('volunteerId')  # List or String of Volunteer IDs
        is_done = data.get('isDone', False)  # Task status, default to False
        date_created = data.get('dateCreated')  # Optional date, defaults to current timestamp

        # Ensure volunteer_ids is an array, even if it's passed as a single string
        if isinstance(volunteer_ids, str):
            volunteer_ids = [volunteer_ids]  # Convert string to a list

        # Validate input
        if not all([name, group_id, volunteer_ids]) or not isinstance(volunteer_ids, list):
            return jsonify({'error': 'Missing required fields or invalid volunteerIds format'}), 400

        # Generate a task ID (you can also let MongoDB auto-generate this if you prefer)
        task_id = str(uuid.uuid4()).replace("-", "")[:12]

        # Prepare the tasks data to insert
        tasks_data = [
            {
                "id": task_id,
                "name": name,
                "groupId": group_id,
                "volunteerId": volunteer_ids,
                "isDone": is_done,
                "dateCreated": date_created
            }
            # for volunteer_id in volunteer_ids
        ]

        # Insert all tasks in one go using insert_many
        database.tasks.insert_many(tasks_data)

        return jsonify({'message': 'Tasks created successfully for all volunteers!'}), 200

    except Exception as e:
        # Log the error for debugging
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


from .verify_token import verify_token

@tasks_bp.route('/get-all-tasks', methods=['GET'])
def get_all_tasks():
    decoded_token = verify_token()
    if decoded_token is None:
         return jsonify({'error': 'Token is invalid or expired'}), 401
    try:
        # Fetch all tasks from the 'tasks' collection
        tasks = list(database.tasks.find())

        # Convert the ObjectId to string for JSON serialization and process volunteers
        for task in tasks:
            task["_id"] = str(task["_id"])  # Convert ObjectId to string

            # Get volunteer data
            volunteer_ids = task.get("volunteerId", [])
            
            # Fetch volunteer details from 'volunteers' collection
            volunteers = []
            for volunteer_id in volunteer_ids:
                volunteer = database.volunteers.find_one({"id": volunteer_id})
                if volunteer:
                    volunteers.append({
                        "firstName": volunteer.get("firstName"),
                        "lastName": volunteer.get("lastName"),
                        "volunteerId": volunteer.get('id')  # Convert ObjectId to string
                    })

            # Add volunteers list to the task
            task["volunteers"] = volunteers

        # Return tasks with volunteer details
        return jsonify(tasks), 200

    except Exception as e:
        # Log the error for debugging
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500
    



@tasks_bp.route('/get-tasks-by-group/<group_id>', methods=['GET'])
def get_tasks_by_group(group_id):
    try:
        # Fetch tasks from the 'tasks' collection filtered by groupId
        tasks = list(database.tasks.find({"groupId": group_id}))

        # Convert the ObjectId to string for JSON serialization and process volunteers
        for task in tasks:
            task["_id"] = str(task["_id"])  # Convert ObjectId to string

            # Get volunteer data
            volunteer_ids = task.get("volunteerId", [])
            
            # Fetch volunteer details from 'volunteers' collection
            volunteers = []
            for volunteer_id in volunteer_ids:
                volunteer = database.volunteers.find_one({"id": volunteer_id})
                if volunteer:
                    volunteers.append({
                        "firstName": volunteer.get("firstName"),
                        "lastName": volunteer.get("lastName"),
                        "volunteerId": volunteer.get("id")  # Ensure the volunteer ID is returned as a string
                    })

            # Add volunteers list to the task
            task["volunteers"] = volunteers

        # Return the tasks with volunteer details
        return jsonify(tasks), 200

    except Exception as e:
        # Log the error for debugging
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500







@tasks_bp.route('/delete-task/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        # Check if the task exists by finding it by its _id (task_id)
        task = database.tasks.find_one({"id": task_id})

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        # Delete the task from the 'tasks' collection
        result = database.tasks.delete_one({"id": task_id})

        # Check if a task was deleted
        if result.deleted_count == 0:
            return jsonify({'error': 'No task deleted'}), 404

        return jsonify({'message': 'Task deleted successfully'}), 200

    except Exception as e:
        # Log the error for debugging
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


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
      

        # Check if the task exists in the MongoDB collection
        task = database.tasks.find_one({"id": task_id})

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        # Prepare the update data
        update_data = {
            "name": name,
            "groupId": group_id,
            "volunteerId": volunteer_ids,  # Replace with new volunteerIds list
            "isDone": is_done,
            "dateCreated": date_created
        }

        # Update the task document in the MongoDB collection
        update_result = database.tasks.update_one({"id": task_id}, {"$set": update_data})

        if update_result.matched_count == 0:
            return jsonify({'error': 'No task found to update'}), 404

        return jsonify({'message': 'Task updated successfully for all volunteers!'}), 200

    except Exception as e:
        # Log the error for debugging
        logging.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500