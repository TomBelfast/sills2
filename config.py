import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///sills.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload configuration
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Rate limiting configuration
    RATELIMIT_DEFAULT = "200 per day"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Application specific configuration
    COLORS = [
        'White',
        'Cream',
        'Anthracite Grey',
        'Mahogony',
        'Rosewood',
        'Black Ash',
        'Oak',
        'Black Grain'
    ]
    
    SILL_TYPES = [
        'Straight',
        'C-shaped',
        'Bay-Curve shaped',
        'Conservatory'
    ]
    
    # OpenAI configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Create upload folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER) 