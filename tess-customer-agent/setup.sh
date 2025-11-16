#!/bin/bash

set -e  # Exit on error

echo "🚀 Setting up TESS Customer Agent..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}Error: Python 3.9 or higher is required. Found: $python_version${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $python_version detected${NC}"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt --quiet

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create data directories
echo -e "${YELLOW}Creating data directories...${NC}"
mkdir -p data/chromadb
mkdir -p data/knowledge_base
mkdir -p logs

echo -e "${GREEN}✓ Data directories created${NC}"

# Check for environment file
ENV=${1:-dev}
if [ ! -f ".env.$ENV" ]; then
    echo -e "${YELLOW}Warning: .env.$ENV not found. Creating from .env.example...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env.$ENV
        echo -e "${YELLOW}Please edit .env.$ENV with your configuration${NC}"
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Environment configuration checked${NC}"

# Check for PostgreSQL connection
echo -e "${YELLOW}Checking PostgreSQL configuration...${NC}"
export $(cat .env.$ENV | grep -v '^#' | xargs)

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo -e "${YELLOW}Warning: PostgreSQL credentials not configured in .env.$ENV${NC}"
else
    echo -e "${GREEN}✓ PostgreSQL configuration found${NC}"

    # Run migrations
    echo -e "${YELLOW}Running database migrations...${NC}"
    python -m src.utils.migrate 2>/dev/null || echo -e "${YELLOW}Note: Migration failed. Make sure PostgreSQL is running and configured correctly.${NC}"
fi

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-api-key-here" ]; then
    echo -e "${YELLOW}Warning: OpenAI API key not configured in .env.$ENV${NC}"
    echo -e "${YELLOW}Please set OPENAI_API_KEY in .env.$ENV${NC}"
else
    echo -e "${GREEN}✓ OpenAI API key configured${NC}"
fi

# Check for Frappe MCP URL
if [ -z "$FRAPPE_MCP_URL" ]; then
    echo -e "${YELLOW}Warning: Frappe MCP URL not configured in .env.$ENV${NC}"
else
    echo -e "${GREEN}✓ Frappe MCP URL configured: $FRAPPE_MCP_URL${NC}"
fi

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit .env.$ENV with your configuration (API keys, database credentials, etc.)"
echo "  2. Make sure PostgreSQL is running"
echo "  3. Make sure your Frappe MCP server is running"
echo "  4. Run database migrations: source venv/bin/activate && python -m src.utils.migrate"
echo "  5. Start the application: ./run.sh $ENV"
echo ""
echo "To activate the virtual environment manually:"
echo "  source venv/bin/activate"
echo ""
