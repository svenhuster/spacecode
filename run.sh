#!/usr/bin/env bash

# LeetCode SRS - Run Script
# This script starts the application using the Nix development environment

echo "🧠 LeetCode Spaced Repetition System"
echo "===================================="
echo ""
echo "Starting in Nix development environment..."
echo ""

# Use nix develop to run the initialization and app startup
nix develop --command bash -c '
echo "Setting up database..."
python3 init_db.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database initialized successfully!"
    echo ""
    echo "🚀 Starting LeetCode SRS application..."
    echo ""
    echo "📍 Server will be available at: http://localhost:1234"
    echo "📖 Visit http://localhost:1234/bookmarklet to install the bookmarklet"
    echo ""
    echo "💡 Quick tips:"
    echo "   - Use keyboard shortcuts 0-5 during practice sessions"
    echo "   - Install the bookmarklet for one-click problem adding"
    echo "   - The app is optimized for 4+ daily practice sessions"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo "======================================"
    echo ""

    # Start the Flask application
    python3 app.py
else
    echo "❌ Failed to initialize database. Please check for errors above."
    exit 1
fi
'