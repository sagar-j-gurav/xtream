#!/bin/bash

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
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TESS Customer Agent${NC}"
echo -e "${BLUE}  Environment: $ENV${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Running setup...${NC}"
    ./setup.sh $ENV
    echo ""
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Load environment variables
if [ ! -f ".env.$ENV" ]; then
    echo -e "${RED}Error: .env.$ENV not found${NC}"
    echo -e "${YELLOW}Please create .env.$ENV from .env.example${NC}"
    exit 1
fi

echo -e "${YELLOW}Loading environment variables from .env.$ENV...${NC}"
export $(cat .env.$ENV | grep -v '^#' | xargs)

# Validate required environment variables
missing_vars=0

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-api-key-here" ]; then
    echo -e "${RED}Error: OPENAI_API_KEY not configured${NC}"
    missing_vars=1
fi

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo -e "${RED}Error: POSTGRES_PASSWORD not configured${NC}"
    missing_vars=1
fi

if [ $missing_vars -eq 1 ]; then
    echo -e "${RED}Please configure missing variables in .env.$ENV${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Environment variables loaded${NC}"

# Run mode based on environment
if [ "$ENV" == "dev" ]; then
    echo -e "${YELLOW}🔧 Starting TESS in DEVELOPMENT mode...${NC}"
    echo ""
    echo -e "${GREEN}Server will auto-reload on code changes${NC}"
    echo -e "${GREEN}Access the API at: http://$APP_HOST:$APP_PORT${NC}"
    echo -e "${GREEN}API documentation: http://$APP_HOST:$APP_PORT/docs${NC}"
    echo ""
    python -m uvicorn src.main:app --reload --host $APP_HOST --port $APP_PORT --log-level ${LOG_LEVEL,,}
else
    echo -e "${YELLOW}🚀 Starting TESS in $ENV mode with PM2...${NC}"

    # Check if PM2 is installed
    if ! command -v pm2 &> /dev/null; then
        echo -e "${RED}Error: PM2 is not installed${NC}"
        echo -e "${YELLOW}Install PM2 with: npm install -g pm2${NC}"
        exit 1
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
