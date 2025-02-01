from flask import Flask
from flask_cors import CORS
from app.login import login_bp
from app.main import main_bp
from app.teams import teams_bp 
from app.volunteers  import volunteers_bp
from app.stats import stats_py;
from app.tasks import tasks_bp
from app.meetings import meetings_bp
 # Import the teams blueprint

def create_app():
    app = Flask(__name__)
    # Apply CORS globally here, for all routes
    CORS(app, resources={r"/*": {"origins": ["http://localhost:4500",'https://scintillating-dasik-a1e6aa.netlify.app','https://rotaract-front-17bdmy7ft-adizhs-projects.vercel.app']}},supports_credentials=True)

    # Register blueprints
    app.register_blueprint(login_bp, url_prefix='/auth')  # Routes under '/auth'
    app.register_blueprint(main_bp)  # Routes directly under root
    app.register_blueprint(teams_bp, url_prefix='/teams')  # Routes under '/teams'
    app.register_blueprint(volunteers_bp, url_prefix='/volunteers')  # Routes under '/teams'
    app.register_blueprint(stats_py, url_prefix='/stats')  # Routes under '/teams'
    app.register_blueprint(tasks_bp, url_prefix='/tasks')  # Routes under '/teams'
    app.register_blueprint(meetings_bp, url_prefix='/meetings')  # Routes under '/teams'

    return app
