import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from flask import Flask
from config import Config
from extensions import db, bootstrap, limiter, migrate
from models import Client, Sill, Settings, MaterialPrices, DefaultSettings
from routes import register_routes

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Sills Application - Window Sills Management System')
    parser.add_argument('--openai-key', 
                       help='OpenAI API key for contract analysis',
                       type=str)
    parser.add_argument('--port', 
                       help='Port to run the application on (default: 56666)',
                       type=int, 
                       default=56666)
    parser.add_argument('--host', 
                       help='Host to run the application on (default: 0.0.0.0)',
                       type=str, 
                       default='0.0.0.0')
    parser.add_argument('--debug', 
                       help='Enable debug mode',
                       action='store_true')
    return parser.parse_args()

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__, static_url_path='', static_folder='static')
    app.config.from_object(config_class)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    bootstrap.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    # Register routes
    register_routes(app)

    return app

def init_db_connection(app):
    """Initialize database connection."""
    try:
        with app.app_context():
            connection = db.engine.connect()
            logger.info("Database connection test:")
            result = connection.execute(db.text("SELECT sqlite_version()"))
            version = result.scalar()
            logger.info(f"Database version: {version}")
            connection.close()
            return True
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        logger.error(f"Connection string: {app.config['SQLALCHEMY_DATABASE_URI']}")
        return False

def auto_manage_database(app):
    """Automatic database management."""
    with app.app_context():
        try:
            # Check database connection
            connection = db.engine.connect()
            logger.info("Checking database connection...")
            
            # Check database version
            result = connection.execute(db.text("SELECT sqlite_version()"))
            version = result.scalar()
            logger.info(f"Database version: {version}")
            
            # Create tables if they don't exist (don't drop existing ones)
            logger.info("Creating tables if they don't exist...")
            db.create_all()
            
            # Initialize default data
            logger.info("Initializing default data...")
            
            # Add default material prices
            if not MaterialPrices.query.first():
                prices = MaterialPrices()
                db.session.add(prices)
                logger.info("Added default material prices")
            
            # Add default settings ONLY if no settings exist
            existing_settings = Settings.query.first()
            if not existing_settings:
                logger.info("No existing settings found, creating new ones...")
                # Check if there are saved default settings
                default_settings = DefaultSettings.query.first()
                if default_settings:
                    # Use saved default settings
                    settings = Settings(
                        plate_length=default_settings.plate_length,
                        length_95mm=default_settings.length_95mm,
                        cutting_allowance=default_settings.cutting_allowance,
                        hot_glue_per_meter=default_settings.hot_glue_per_meter,
                        glue_with_activator_per_meter=default_settings.glue_with_activator_per_meter,
                        silicone_per_meter=default_settings.silicone_per_meter,
                        silicone_color_per_meter=default_settings.silicone_color_per_meter,
                        pvc_cleaner_per_meter=default_settings.pvc_cleaner_per_meter,
                        fixall_per_meter=default_settings.fixall_per_meter,
                        glue_color_extra=default_settings.glue_color_extra
                    )
                    logger.info(f"Created settings from saved defaults: cutting_allowance={default_settings.cutting_allowance}, glue_color_extra={default_settings.glue_color_extra}")
                else:
                    # Use built-in default settings
                    settings = Settings()
                    logger.info(f"Created built-in default settings: cutting_allowance={settings.cutting_allowance}, glue_color_extra={settings.glue_color_extra}")
                db.session.add(settings)
            else:
                logger.info(f"Existing settings found: cutting_allowance={existing_settings.cutting_allowance}, glue_color_extra={existing_settings.glue_color_extra}")
            
            # Add default settings template
            if not DefaultSettings.query.first():
                default_settings = DefaultSettings()
                db.session.add(default_settings)
                logger.info("Added default settings template")
            
            db.session.commit()
            logger.info("Database initialization completed successfully")
            
            connection.close()
            return True
            
        except Exception as e:
            logger.error(f"Database management error: {str(e)}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    # Parse command line arguments
    args = parse_arguments()
    
    # Set OpenAI API key from command line if provided
    if args.openai_key:
        os.environ['OPENAI_API_KEY'] = args.openai_key
        logger.info("OpenAI API key set from command line argument")
        logger.info(f"API key: {args.openai_key[:10]}...{args.openai_key[-4:] if len(args.openai_key) > 14 else '***'}")
    
    # Check if OpenAI API key is available
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        logger.info("OpenAI API key is available - contract analysis enabled")
    else:
        logger.warning("No OpenAI API key found. Contract analysis will be limited.")
        logger.info("To enable contract analysis, use one of these methods:")
        logger.info("  1. Set environment variable: set OPENAI_API_KEY=your-api-key")
        logger.info("  2. Use command line: python app.py --openai-key YOUR_API_KEY")
        logger.info("  3. Create .env file with: OPENAI_API_KEY=your-api-key")
    
    app = create_app()
    if init_db_connection(app):
        if auto_manage_database(app):
            logger.info("Database management completed successfully")
            logger.info(f"Starting application on {args.host}:{args.port}")
            app.run(host=args.host, port=args.port, debug=args.debug)
        else:
            logger.error("Failed to manage database")
    else:
        logger.error("Could not start application due to database connection error")
