from flask import Flask, request, jsonify, send_from_directory
import requests
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from flask_cors import CORS
import logging
import os
import time

# this is make for debugging purposes only.. remove in production!!
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# front end stuff here we serve it from flask
app = Flask(__name__, static_folder="chat-interface")

# this remove cors problem when run locally  
CORS(app)  

# sqlite is used for simple testing purpose
# u can change to other db later when needs more powerfull
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///prompts.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# this where Ollama API located at dont change if ollama running local
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODELS_URL = "http://127.0.0.1:11434/api/tags"

# this settings control how we call ollama
CONFIG = {
    "primary_model": "codellama",
    "fallback_model": "mistral:latest",
    "request_timeout": 120,  
    "max_retries": 2,
    "retry_delay": 2,  # Seconds to wait between retries
}

# this prompt used for all chat not optimized yet still work on it
SYSTEM_PROMPT = """
You are an expert Python tutor focused exclusively on Python programming and related libraries/frameworks like Flask, Django, FastAPI, Pandas, NumPy, Matplotlib, PyTorch, TensorFlow, and other Python ecosystems. You will ONLY respond to questions related to Python programming or Python libraries/frameworks.

IF a question is not related to Python or its ecosystem:
- Politely inform the user that you're a specialized Python tutor and can only assist with Python-related questions
- Do not attempt to answer non-Python questions even if you know the answer
- Suggest they rephrase their question to relate it to Python if possible

When responding to Python-related questions:
- Begin with a clear, detailed explanation of the concept or problem before providing code or solutions
- Use real-world examples, best practices, and optimization techniques to illustrate your points
- Tailor explanations to be accessible to beginners while remaining precise and technically accurate for advanced learners
- When debugging, identify the root cause of the issue and explain it step-by-step before suggesting fixes
- Structure responses logically with headings, bullet points, or numbered steps for readability
- If a user's question is vague, ask clarifying questions to provide the most relevant answer
- Encourage good coding habits, such as modularity, documentation, and error handling
- Include working code examples that demonstrate the concepts being taught

Remember: You are STRICTLY a Python tutor. Any question not related to Python programming or its ecosystem should be politely declined.
"""

# predefine prompts for user to use so they dont type similar stuff
# might add more later this just first version
PREDEFINED_PROMPTS = [
    "Explain Python context managers and provide an example using 'with' statements.",
    "How do I build a Flask app with user authentication and session management?",
    "Write a Python script to fetch and parse JSON data from a public API.",
    "What are Python generators, and how can they improve memory efficiency?",
    "How do I integrate Flask with a PostgreSQL database using SQLAlchemy?",
    "Explain Python's Global Interpreter Lock (GIL) and its impact on multithreading.",
    "Create a Flask API to upload and process image files with error handling.",
    "How do I use Python's 'asyncio' library to handle asynchronous tasks?",
    "Write a Python script to analyze a log file and extract specific patterns.",
    "Explain dependency injection in Python with a Flask example.",
    "How do I secure a Flask API with OAuth 2.0 authentication?",
    "What are the differences between Flask and Django, and when should I use each?",
    "Write a Python function to compress a folder into a ZIP file.",
    "How do I implement a caching mechanism in Flask using Redis?",
    "Explain how to use Python's 'unittest' framework with a practical example."
]

# database table setup for save prompts
# track if api call was succesfull or not
class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    is_predefined = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    successful = db.Column(db.Boolean, default=True)  # Track if the prompt was successfully

    def __repr__(self):
        return f"<Prompt {self.id}: {self.text[:30]}...>"

# this function create db tables and add predefine prompts
def initialize_database():
    """Create database tables and populate with predefined prompts if they don't exist"""
    with app.app_context():
        db.create_all()
        
        # Add predefined prompts if they don't exist
        for prompt_text in PREDEFINED_PROMPTS:
            existing_prompt = Prompt.query.filter_by(text=prompt_text).first()
            if not existing_prompt:
                logger.info(f"Adding predefined prompt: {prompt_text[:30]}...")
                db.session.add(Prompt(text=prompt_text, is_predefined=True))
        
        db.session.commit()
        logger.info("Database initialization complete")

# check if ollama running and what models available
def check_ollama_service():
    """Check if Ollama service is running and return available models"""
    try:
        response = requests.get(OLLAMA_MODELS_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            # Extract model names and remove version tags for matching
            available_models = [model.get("name") for model in models]
            available_model_names = [model.split(':')[0] for model in available_models]
            
            logger.info(f"Found models: {available_models}")
            
            # Check if primary or fallback models are available (with or without version tag)
            primary_available = (CONFIG["primary_model"] in available_models or 
                               CONFIG["primary_model"] in available_model_names)
            
            fallback_available = (CONFIG["fallback_model"] in available_models or
                                CONFIG["fallback_model"] in available_model_names)
            
            return {
                "status": "ok",
                "available_models": available_models,
                "primary_model_available": primary_available,
                "fallback_model_available": fallback_available
            }
        else:
            return {"status": "error", "message": f"Ollama service returned status code {response.status_code}"}
    except requests.RequestException as e:
        return {"status": "error", "message": f"Ollama service unavailable: {str(e)}"}

# find model that match what we want even if version different
def get_matching_model(requested_model):
    """Find a matching model from available models"""
    try:
        response = requests.get(OLLAMA_MODELS_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            available_models = [model.get("name") for model in models]
            
            # Check for exact match first
            if requested_model in available_models:
                return requested_model
            
            # Check for match without version
            requested_base = requested_model.split(':')[0]
            for model in available_models:
                model_base = model.split(':')[0]
                if model_base == requested_base:
                    logger.info(f"Using model {model} for requested model {requested_model}")
                    return model
            
            return None
        else:
            logger.error(f"Could not get models list: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error finding matching model: {str(e)}")
        return None

# send request to ollama and retry if failed
def send_ollama_request(prompt, model_name, max_retries=2):
    """Send request to Ollama API with retry logic"""
    # Find the actual model name that matches the requested one
    model_to_use = get_matching_model(model_name)
    if not model_to_use:
        return None, f"Model matching '{model_name}' not found"
    
    payload = {
        "model": model_to_use,
        "prompt": prompt,
        "stream": False
    }
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Sending request to model {model_to_use} (attempt {attempt+1}/{max_retries+1})")
            start_time = time.time()
            response = requests.post(OLLAMA_URL, json=payload, timeout=CONFIG["request_timeout"])
            elapsed_time = time.time() - start_time
            logger.info(f"Request completed in {elapsed_time:.2f} seconds")
            
            if response.status_code == 200:
                return response.json().get("response"), None
            else:
                error_msg = f"Ollama API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                
                if attempt < max_retries:
                    logger.info(f"Retrying in {CONFIG['retry_delay']} seconds...")
                    time.sleep(CONFIG["retry_delay"])
                else:
                    return None, error_msg
        except requests.Timeout:
            error_msg = f"Request timed out after {CONFIG['request_timeout']} seconds"
            logger.error(error_msg)
            
            if attempt < max_retries:
                logger.info(f"Retrying in {CONFIG['retry_delay']} seconds...")
                time.sleep(CONFIG["retry_delay"])
            else:
                return None, error_msg
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            
            if attempt < max_retries:
                logger.info(f"Retrying in {CONFIG['retry_delay']} seconds...")
                time.sleep(CONFIG["retry_delay"])
            else:
                return None, error_msg
    
    return None, "Maximum retries exceeded"

# save prompt to db for later use
def save_prompt(text, successful=True):
    """Save a user prompt to the database if it's not already there"""
    if text not in PREDEFINED_PROMPTS:
        existing_prompt = Prompt.query.filter_by(text=text).first()
        if not existing_prompt:
            try:
                new_prompt = Prompt(text=text, is_predefined=False, successful=successful)
                db.session.add(new_prompt)
                db.session.commit()
                logger.info(f"Saved new prompt (id: {new_prompt.id})")
                return new_prompt
            except Exception as e:
                logger.error(f"Error saving prompt: {str(e)}")
                db.session.rollback()
        else:
            logger.info(f"Prompt already exists (id: {existing_prompt.id})")
            return existing_prompt
    return None

# main endpoint for chat functionality
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message", "")
    
    if not user_input:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    # Log the incoming request
    logger.info(f"Received chat request: {user_input[:50]}...")
    
    # Check Ollama service health
    service_status = check_ollama_service()
    if service_status["status"] != "ok":
        logger.error(f"Ollama service check failed: {service_status['message']}")
        return jsonify({"error": service_status["message"]}), 503
    
    # Save prompt before processing (mark as not successful yet)
    prompt_record = save_prompt(user_input, successful=False)
    
    # Prepare full prompt with system context
    full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_input}\nAssistant:"
    
    # Try primary model first if available
    if service_status["primary_model_available"]:
        logger.info(f"Attempting request with primary model: {CONFIG['primary_model']}")
        response, error = send_ollama_request(full_prompt, CONFIG["primary_model"], CONFIG["max_retries"])
        
        if response:
            # Update prompt record as successful
            if prompt_record:
                prompt_record.successful = True
                db.session.commit()
            return jsonify({"response": response})
    else:
        logger.warning(f"Primary model {CONFIG['primary_model']} not available")
        # Check if any model is available and use that
        if service_status["available_models"]:
            available_model = service_status["available_models"][0]
            logger.info(f"Using available model: {available_model}")
            response, error = send_ollama_request(full_prompt, available_model, CONFIG["max_retries"])
            
            if response:
                # Update prompt record as successful
                if prompt_record:
                    prompt_record.successful = True
                    db.session.commit()
                return jsonify({
                    "response": response,
                    "note": f"Used available model {available_model} instead of requested primary model"
                })
        error = f"Primary model {CONFIG['primary_model']} not available and no suitable alternative found"
    
    # If primary model failed and fallback is available, try fallback
    if service_status["fallback_model_available"]:
        logger.info(f"Primary model failed. Trying fallback model: {CONFIG['fallback_model']}")
        response, fallback_error = send_ollama_request(full_prompt, CONFIG["fallback_model"], CONFIG["max_retries"])
        
        if response:
            # Update prompt record as successful
            if prompt_record:
                prompt_record.successful = True
                db.session.commit()
            return jsonify({
                "response": response,
                "note": f"Used fallback model {CONFIG['fallback_model']} due to issue with primary model"
            })
        error = f"{error}. Fallback also failed: {fallback_error}"
    else:
        logger.warning(f"Fallback model {CONFIG['fallback_model']} not available")
        error = f"{error}. Fallback model {CONFIG['fallback_model']} not available"
    
    logger.error(f"All model attempts failed: {error}")
    return jsonify({"error": f"Failed to get response: {error}"}), 500

# get all prompts both predefined and user entered
@app.route("/prompts", methods=["GET"])
def get_prompts():
    try:
        predefined = Prompt.query.filter_by(is_predefined=True).all()
        user_prompts = Prompt.query.filter_by(is_predefined=False).order_by(Prompt.created_at.desc()).all()
        
        return jsonify({
            "predefined_prompts": [p.text for p in predefined],
            "user_prompts": [
                {
                    "id": p.id,
                    "text": p.text, 
                    "created_at": p.created_at.isoformat(),
                    "successful": p.successful
                } for p in user_prompts
            ]
        })
    except Exception as e:
        logger.error(f"Error retrieving prompts: {str(e)}")
        return jsonify({"error": str(e)}), 500

# check if system working ok
@app.route("/health", methods=["GET"])
def health_check():
    """API endpoint to check system health"""
    try:
        # Check database
        db_status = "ok"
        try:
            # Use SQLAlchemy text() function for proper query declaration
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Check Ollama service
        ollama_status = check_ollama_service()
        
        # Consider server healthy if Ollama is working, even if database has issues
        server_status = "ok" if ollama_status["status"] == "ok" else "error"
        
        return jsonify({
            "status": server_status,
            "database": db_status,
            "ollama": ollama_status,
            "config": {
                "primary_model": CONFIG["primary_model"],
                "fallback_model": CONFIG["fallback_model"],
                "request_timeout": CONFIG["request_timeout"],
                "max_retries": CONFIG["max_retries"]
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500

# delete all user prompt but keep predefine ones
@app.route("/clear-prompts", methods=["POST"])
def clear_user_prompts():
    """Clear user prompts but keep predefined ones"""
    try:
        # Delete all non-predefined prompts
        deleted = Prompt.query.filter_by(is_predefined=False).delete()
        db.session.commit()
        logger.info(f"Cleared {deleted} user prompts")
        return jsonify({"status": "success", "deleted_count": deleted})
    except Exception as e:
        logger.error(f"Error clearing prompts: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# serve the main page
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# serve all other files from static folder
@app.route('/<path:path>')
def serve_static(path):
    try:
        return send_from_directory(app.static_folder, path)
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        return jsonify({"error": "File not found"}), 404

# no favicon dont waste time lookup
@app.route('/favicon.ico')
def favicon():
    return '', 204  # No content response to silence the request

# handle errors with json responses
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

# setup database when app start
initialize_database()

if __name__ == "__main__":
    # make sure logs folder exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
        
    # Log application startup
    logger.info("Starting Flask-Ollama application")
    logger.info(f"Configuration: {CONFIG}")
    
    # Check Ollama service on startup
    service_status = check_ollama_service()
    logger.info(f"Ollama service status: {service_status}")
    
    # Start the Flask application
    app.run(debug=True, port=5000)