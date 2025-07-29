#!/bin/bash

# Colify Deployment Script for Sills Application - PRAWDZIWE DANE
# This script automates the deployment process on Colify

set -e

echo "🚀 Starting Colify deployment for Sills application..."

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found. Please run this script from the project root."
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p uploads
mkdir -p static/css
mkdir -p static/js
mkdir -p templates
mkdir -p instance

# Check Python version
echo "🐍 Checking Python version..."
python --version

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Set environment variables for production - PRAWDZIWE DANE
export FLASK_ENV=production
export FLASK_DEBUG=False
export SECRET_KEY=${SECRET_KEY:-"your-secret-key"}
export DATABASE_URL=${DATABASE_URL:-"sqlite:///sills.db"}
export SQLALCHEMY_TRACK_MODIFICATIONS=False
export UPLOAD_FOLDER=${UPLOAD_FOLDER:-"uploads"}
export MAX_CONTENT_LENGTH=${MAX_CONTENT_LENGTH:-16777216}
export ALLOWED_EXTENSIONS=${ALLOWED_EXTENSIONS:-"png,jpg,jpeg,gif,pdf"}
export RATELIMIT_DEFAULT=${RATELIMIT_DEFAULT:-"200 per day"}
export RATELIMIT_STORAGE_URL=${RATELIMIT_STORAGE_URL:-"memory://"}
export PORT=${PORT:-56666}
export HOST=${HOST:-"0.0.0.0"}
export FLASK_APP=app.py
export PYTHONPATH=/app

# Initialize database
echo "🗄️ Initializing database..."
python -c "
from app import create_app, auto_manage_database
app = create_app()
auto_manage_database(app)
print('Database initialized successfully')
"

# Check if database was created
if [ -f "sills.db" ]; then
    echo "✅ Database file created successfully"
else
    echo "⚠️ Warning: Database file not found, will be created on first run"
fi

# Set proper permissions
echo "🔐 Setting proper permissions..."
chmod 755 uploads
chmod 755 instance
chmod 644 *.py
chmod 644 requirements.txt

# Test the application
echo "🧪 Testing application startup..."
python -c "
from app import create_app
app = create_app()
print('✅ Application created successfully')
"

echo "🎉 Deployment preparation completed!"
echo ""
echo "📋 Next steps:"
echo "1. Set environment variables in Colify dashboard"
echo "2. Deploy to Colify"
echo "3. Check application logs"
echo ""
echo "🔧 Environment variables to set in Colify - PRAWDZIWE DANE:"
echo "SECRET_KEY=your-secret-key"
echo "FLASK_ENV=production"
echo "FLASK_DEBUG=False"
echo "DATABASE_URL=sqlite:///sills.db"
echo "SQLALCHEMY_TRACK_MODIFICATIONS=False"
echo "UPLOAD_FOLDER=uploads"
echo "MAX_CONTENT_LENGTH=16777216"
echo "ALLOWED_EXTENSIONS=png,jpg,jpeg,gif,pdf"
echo "RATELIMIT_DEFAULT=200 per day"
echo "RATELIMIT_STORAGE_URL=memory://"
echo "PORT=56666"
echo "HOST=0.0.0.0"
echo "FLASK_APP=app.py"
echo "PYTHONPATH=/app"
echo ""
echo "📖 For detailed instructions, see COLIFY_INSTALLATION.md"