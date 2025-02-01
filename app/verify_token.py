from flask import request
import jwt
import os
from dotenv import load_dotenv
load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')

def verify_token():
    token = request.headers.get('Authorization')
    if not token:
        return None

    token = token.split(' ')[1]  # Get the actual token (remove 'Bearer' part)
    try:
        # Decode the JWT
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return decoded_token
    # except jwt.ExpiredSignatureError:
    #     return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token