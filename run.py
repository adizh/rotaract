from flask import Flask, jsonify

app = Flask(__name__)

from app import create_app


app = create_app()



       
            

if __name__ == '__main__':
    app.run(debug=True)
