from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

# Initialize extensions
db = SQLAlchemy()
bootstrap = Bootstrap()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate() 