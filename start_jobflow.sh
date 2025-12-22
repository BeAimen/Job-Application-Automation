#!/bin/bash
# JobFlow macOS/Linux Launcher
# Make executable: chmod +x start_jobflow.sh
# Run: ./start_jobflow.sh

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "========================================"
echo "  Starting JobFlow..."
echo "========================================"
echo ""

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source .venv/bin/activate
else
    echo -e "${RED}Warning: Virtual environment not found!${NC}"
    echo "Please run: python3 -m venv .venv"
    echo "Then run: source .venv/bin/activate"
    echo "Then run: pip install -r requirements.txt"
    exit 1
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}Python not found in virtual environment!${NC}"
    exit 1
fi

# Start the launcher
python launcher.py

# Check exit status
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}Press Enter to close...${NC}"
    read
fi