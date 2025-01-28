from flask import Flask, jsonify
from pymongo import MongoClient
import pymongo
from pymongo import MongoClient
app = Flask(__name__)
from urllib.parse import quote_plus
import ssl
import os
ssl._create_default_https_context = ssl._create_unverified_context
#CONNECTION_STRING = f"mongodb+srv://{app.config['USER_NAME']}:{app.config['USER_PASSWORD']}@cluster0.it8fp.mongodb.net/users?retryWrites=true&w=majority&appName=Cluster0"
username = os.getenv('USER_NAME')
password = os.getenv('USER_PASSWORD')
CONNECTION_STRING = f"mongodb+srv://{username}:{password}@cluster0.it8fp.mongodb.net/users?retryWrites=true&w=majority&appName=Cluster0"


client = MongoClient(CONNECTION_STRING)

users_collection = client.users['users']

# Fetch all documents from the 'users' collection using find()

# Print each document in the collection

# if client:
#     print("connected")
# else: 
#     print("not connected")
@app.route('/')
def index():
     users = list(users_collection.find({}, {"_id": 0}))  # Exclude _id for JSON compatibility

    # Return all users as a JSON response
     return jsonify(users)
    # users = users_collection.find()
    # print(users)
    # for user in users:
    #  print("EACJ SUER",user)
    # for user in users:
    #     return {'name':user.name}

      
       
     
        

if __name__ == '__main__':
    app.run(debug=True)
