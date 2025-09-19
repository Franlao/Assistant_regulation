#!/bin/bash
set -e

echo "Building React component for Railway deployment..."

# Check if Node.js is available
if command -v node &> /dev/null; then
    echo "Node.js found: $(node --version)"

    # Check if npm is available
    if command -v npm &> /dev/null; then
        echo "npm found: $(npm --version)"

        # Build React component
        cd components/modern_auth
        echo "Installing React component dependencies..."
        npm ci --only=production

        echo "Building React component..."
        npm run build

        echo "React component built successfully!"
        ls -la dist/

        cd ../..
    else
        echo "npm not found - skipping React build"
    fi
else
    echo "Node.js not found - skipping React build"
fi

# Créer les répertoires de base de données persistante
echo "Creating persistent database directories..."
mkdir -p /app/DB/chroma_db
mkdir -p /app/logs
mkdir -p /app/joblib_cache
mkdir -p /app/.conversation_memory
mkdir -p /app/temp

echo "Database directories created:"
ls -la /app/DB/

echo "Railway build completed!"