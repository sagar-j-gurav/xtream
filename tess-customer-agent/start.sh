#!/bin/bash

# TESS Quick Start Script
# Combines setup and run into a single command
# Usage: ./start.sh [dev|uat|prod]
# Or source it to keep venv active: source start.sh dev

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get environment (default to dev)
ENV=${1:-dev}

# Validate environment
if [ "$ENV" != "dev" ] && [ "$ENV" != "uat" ] && [ "$ENV" != "prod" ]; then
    echo -e "${RED}Error: Invalid environment '$ENV'. Must be one of: dev, uat, prod${NC}"
    return 1 2>/dev/null || exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TESS Quick Start${NC}"
echo -e "${BLUE}  Environment: $ENV${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Setup if needed
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Running setup...${NC}"
    ./setup.sh $ENV
    echo ""
fi

# Step 2: Activate virtual environment
if [ -d "venv" ]; then
    echo -e "${YELLOW}🔌 Activating virtual environment...${NC}"
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}Error: Virtual environment not found${NC}"
    return 1 2>/dev/null || exit 1
fi

# Step 3: Load environment variables
if [ ! -f ".env.$ENV" ]; then
    echo -e "${RED}Error: .env.$ENV not found${NC}"
    echo -e "${YELLOW}Please create .env.$ENV from .env.example and configure it${NC}"
    return 1 2>/dev/null || exit 1
fi

echo -e "${YELLOW}⚙️  Loading environment variables from .env.$ENV...${NC}"
set -a
source .env.$ENV
set +a
echo -e "${GREEN}✓ Environment variables loaded${NC}"

# Step 4: Validate required environment variables
missing_vars=0

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-api-key-here" ]; then
    echo -e "${RED}⚠️  Warning: OPENAI_API_KEY not configured${NC}"
    missing_vars=1
fi

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo -e "${RED}⚠️  Warning: POSTGRES_PASSWORD not configured${NC}"
    missing_vars=1
fi

if [ $missing_vars -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}Please configure missing variables in .env.$ENV before running${NC}"
    echo ""
    echo "You can now:"
    echo -e "  1. Edit .env.$ENV with your configuration"
    echo -e "  2. Run migrations: ${GREEN}python -m src.utils.migrate${NC}"
    echo -e "  3. Start TESS: ${GREEN}python -m uvicorn src.main:app --reload${NC}"
    echo ""
    return 1 2>/dev/null || exit 1
fi

echo ""
echo -e "${GREEN}✅ All checks passed!${NC}"
echo ""

# Step 5: Start the application
if [ "$ENV" == "dev" ]; then
    echo -e "${YELLOW}🚀 Starting TESS in DEVELOPMENT mode...${NC}"
    echo ""
    echo -e "${GREEN}Server will auto-reload on code changes${NC}"
    echo -e "${GREEN}Access the API at: http://$APP_HOST:$APP_PORT${NC}"
    echo -e "${GREEN}API documentation: http://$APP_HOST:$APP_PORT/docs${NC}"
    echo ""
    echo -e "${BLUE}Press Ctrl+C to stop${NC}"
    echo ""

    # Start with uvicorn
    # Convert LOG_LEVEL to lowercase (compatible with bash 3.2+)
    LOG_LEVEL_LOWER=$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')
    python -m uvicorn src.main:app --reload --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8000} --log-level $LOG_LEVEL_LOWER
else
    echo -e "${YELLOW}🚀 Starting TESS in $ENV mode with PM2...${NC}"

    # Check if PM2 is installed
    if ! command -v pm2 &> /dev/null; then
        echo -e "${RED}Error: PM2 is not installed${NC}"
        echo -e "${YELLOW}Install PM2 with: npm install -g pm2${NC}"
        return 1 2>/dev/null || exit 1
    fi

    # Start with PM2
    pm2 start ecosystem.config.js --env $ENV

    echo ""
    echo -e "${GREEN}✓ TESS started with PM2${NC}"
    echo ""
    echo "Commands:"
    echo "  pm2 status           - Check application status"
    echo "  pm2 logs tess-$ENV   - View logs"
    echo "  pm2 restart tess-$ENV - Restart application"
    echo "  pm2 stop tess-$ENV   - Stop application"
    echo "  pm2 monit            - Monitor application"
    echo ""
fi
