from flask import Flask
from config import Config
from extensions import db, bootstrap, limiter, migrate
from models import Client, Sill, Settings, MaterialPrices, DefaultSettings
from routes import register_routes
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

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
    app = create_app()
    if init_db_connection(app):
        if auto_manage_database(app):
            logger.info("Database management completed successfully")
            app.run(host='0.0.0.0', port=55555, debug=True)
        else:
            logger.error("Failed to manage database")
    else:
        logger.error("Could not start application due to database connection error")
