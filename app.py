import os
import re
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import markdown2

# Import your existing CodeCredX flow
from flow import create_codecredx_flow
from main import setup_logging

# --- App Configuration ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///candidates.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'a-secure-random-secret-key' # Change this in production

db = SQLAlchemy(app)
logger = setup_logging()
codecredx_flow = create_codecredx_flow()

# --- Database Model ---
class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    github_username = db.Column(db.String(100), nullable=False)
    overall_score = db.Column(db.Float, nullable=False)
    elo_score = db.Column(db.Float, nullable=False)
    report_markdown = db.Column(db.Text, nullable=False)
    
    def __repr__(self):
        return f'<Candidate {self.github_username}>'

# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_username_from_url(url):
    match = re.search(r'github\.com/([a-zA-Z0-9_-]+)', url, re.IGNORECASE)
    return match.group(1) if match else "N/A"

# --- Web Routes ---
@app.route('/')
def index():
    """Renders the main submission form."""
    return render_template('index.html')

@app.route('/leaderboard')
def leaderboard():
    """Displays all candidates ranked by Elo score."""
    candidates = Candidate.query.order_by(Candidate.elo_score.desc()).all()
    return render_template('leaderboard.html', candidates=candidates)

@app.route('/report/<int:candidate_id>')
def report(candidate_id):
    """Displays the detailed report for a single candidate."""
    candidate = Candidate.query.get_or_404(candidate_id)
    # Convert markdown report to HTML for rendering
    report_html = markdown2.markdown(candidate.report_markdown)
    return render_template('report.html', candidate=candidate, report_html=report_html)

@app.route('/submit', methods=['POST'])
def submit():
    """Handles the form submission and runs the analysis."""
    github_url = request.form.get('github_profile')
    resume_file = request.files.get('resume_file')
    
    if not github_url and (not resume_file or resume_file.filename == ''):
        flash('Please provide a GitHub Profile URL or a resume file.', 'error')
        return redirect(url_for('index'))

    resume_path = None
    if resume_file and allowed_file(resume_file.filename):
        filename = secure_filename(resume_file.filename)
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        resume_file.save(resume_path)
        logger.info(f"Saved uploaded resume to {resume_path}")

    # Prepare the shared dictionary for the flow
    shared = {
        "resume_file_path": resume_path,
        "github_profile_url": github_url,
        "resume_text": None,
        "github_project_urls": [],
        "other_urls": [],
        "analyzed_github_projects": [],
        "overall_candidate_metrics": {},
        "candidate_report": "Processing...",
    }
    
    logger.info("Starting CodeCredX flow from web submission...")
    # NOTE: In a production app, this should be offloaded to a background worker (e.g., Celery)
    # to avoid long request timeouts. For this example, we run it synchronously.
    try:
        codecredx_flow.run(shared)
        logger.info("CodeCredX flow completed successfully.")
    except Exception as e:
        logger.critical(f"An error occurred during flow execution: {e}", exc_info=True)
        flash('An unexpected error occurred during analysis.', 'error')
        return redirect(url_for('index'))

    # Extract results from the shared dictionary
    metrics = shared.get("overall_candidate_metrics", {})
    report_md = shared.get("candidate_report", "Report could not be generated.")
    
    # Save results to the database
    new_candidate = Candidate(
        github_username=extract_username_from_url(github_url) if github_url else "From_Resume",
        overall_score=metrics.get('overall_candidate_score', 0.0),
        elo_score=metrics.get('elo_score', 800.0),
        report_markdown=report_md
    )
    db.session.add(new_candidate)
    db.session.commit()
    logger.info(f"Saved new candidate (ID: {new_candidate.id}) to database.")

    # Redirect to the new candidate's report page
    return redirect(url_for('report', candidate_id=new_candidate.id))

# --- Main Entry Point ---
if __name__ == '__main__':
    with app.app_context():
        # Create the database and tables if they don't exist
        db.create_all()
    # Run the web server
    app.run(debug=True, port=5001)