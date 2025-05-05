#!/bin/bash
# Clara AI Startup Script
# This script checks if Ollama is installed and running, 
# ensures the required model is available, and launches the Clara AI application.

# ANSI color codes for prettier output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default model to use if none specified
DEFAULT_MODEL="qwen3:4b"

# Function to show usage information
show_usage() {
    echo -e "${BOLD}Usage:${NC} ./start.sh [--model MODEL_NAME] [application args...]"
    echo
    echo -e "${BOLD}Options:${NC}"
    echo "  --model MODEL_NAME    Specify which Ollama model to use"
    echo "                        Default: $DEFAULT_MODEL"
    echo
    echo -e "${BOLD}Available Models:${NC}"
    echo "  mixtral:8x7b-instruct  - Mixtral's powerful mixture-of-experts model (recommended)"
    echo "  llama3:70b             - Llama 3's larger 70B parameter model (high performance)"
    echo "  claude-3-haiku         - Anthropic's efficient model"
    echo "  llama3:8b              - Original Llama 3 small model"
    echo "  mistral:7b-instruct    - Efficient instruction-tuned model"
    echo "  qwen2:72b              - Alibaba's large model"
    echo "  phi-3:mini             - Microsoft's compact, efficient model"
    echo
    echo "All standard Clara AI arguments are also supported after the model selection"
    echo "Example: ./start.sh --model llama3:70b --interval 30 --debug"
    exit 1
}

# Parse command line arguments for model selection
MODEL_NAME="$DEFAULT_MODEL"
APP_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            if [[ -z $2 || $2 == --* ]]; then
                echo -e "${RED}Error: --model requires a model name${NC}"
                show_usage
            fi
            MODEL_NAME="$2"
            shift 2
            ;;
        --help|-h)
            show_usage
            ;;
        *)
            APP_ARGS+=("$1")
            shift
            ;;
    esac
done

# Variable to track if we started Ollama or if it was already running
OLLAMA_WAS_STARTED_BY_SCRIPT=false
# Flag to prevent multiple executions of cleanup
CLEANUP_EXECUTED=false

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to clean up before exit
cleanup() {
    # Prevent multiple executions
    if [ "$CLEANUP_EXECUTED" = true ]; then
        return
    fi
    CLEANUP_EXECUTED=true
    
    echo
    echo -e "${BLUE}Shutting down Clara AI...${NC}"
    
    # Deactivate virtualenv if activated
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate 2>/dev/null || true
        echo -e "${GREEN}✓ Virtual environment deactivated.${NC}"
    fi
    
    # Shutdown Ollama if we started it
    if [ "$OLLAMA_WAS_STARTED_BY_SCRIPT" = true ]; then
        echo -e "${BLUE}Shutting down Ollama service...${NC}"
        # Find and kill the Ollama process
        if command_exists pkill; then
            pkill -x ollama 2>/dev/null || true
        else
            # Fallback to more generic approach if pkill is not available
            PID=$(pgrep -x ollama 2>/dev/null)
            if [ -n "$PID" ]; then
                kill $PID 2>/dev/null || true
            fi
        fi
        echo -e "${GREEN}✓ Ollama service stopped.${NC}"
    fi
    
    echo -e "${GREEN}Clara AI has been stopped.${NC}"
    # Don't use exit here, as it can cause recursive trap execution
}

# Set up trap to call cleanup function on exit
trap cleanup EXIT INT TERM

# Function to display a progress bar
display_progress() {
    local width=50
    local progress=$1
    local percentage=$2
    
    # Create the progress bar
    local filled=$((width * progress / 100))
    local empty=$((width - filled))
    
    # Print the progress bar
    printf "\r["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "] %3d%%" "$percentage"
}

# Function to handle model download with progress bar
download_model_with_progress() {
    local model=$1
    local download_size=0
    local current_size=0
    local percentage=0
    local progress=0
    local temp_file=".download_progress.tmp"
    
    echo -e "${YELLOW}${model} model not found. Downloading...${NC}"
    
    # Start download in background and capture progress to temp file
    ollama pull $model 2>&1 | tee $temp_file &
    local pid=$!
    
    # Monitor the download progress
    while kill -0 $pid 2>/dev/null; do
        if grep -q "downloading" $temp_file; then
            # Extract the size information using grep and awk
            if [[ -z "$download_size" || "$download_size" == "0" ]]; then
                download_size=$(grep -o "[0-9.]\+\(MB\|GB\)" $temp_file | tail -n1 | grep -o "[0-9.]\+")
                # If size is in GB, convert to MB
                if grep -q "GB" $temp_file; then
                    download_size=$(echo "$download_size * 1024" | bc)
                fi
            fi
            
            # Get current download progress
            current_size=$(grep -o "[0-9.]\+/[0-9.]\+\(MB\|GB\)" $temp_file | tail -n1 | awk -F'/' '{print $1}')
            
            # Calculate percentage if we have valid numbers
            if [[ -n "$download_size" && "$download_size" != "0" && -n "$current_size" ]]; then
                if grep -q "GB" $temp_file && ! echo "$current_size" | grep -q "GB"; then
                    # Convert current_size to GB for calculation
                    percentage=$(echo "scale=2; ($current_size / $download_size) * 100" | bc)
                    progress=$(echo "$percentage / 1" | bc)  # Remove decimal part
                else
                    percentage=$(echo "scale=2; ($current_size / $download_size) * 100" | bc)
                    progress=$(echo "$percentage / 1" | bc)  # Remove decimal part
                fi

                # Ensure the progress is within bounds
                if [[ "$progress" -gt 100 ]]; then
                    progress=100
                fi
                if [[ "$progress" -lt 0 ]]; then
                    progress=0
                fi
                
                # Display the progress bar
                display_progress $progress $progress
            fi
        fi
        sleep 0.2
    done
    
    # Cleanup
    wait $pid
    rm -f $temp_file
    echo -e "\n${GREEN}✓ ${model} model downloaded successfully.${NC}"
}

# Check if Ollama is installed
echo -e "${BLUE}Checking Ollama installation...${NC}"
if ! command_exists ollama; then
    echo -e "${RED}Ollama is not installed. Please install Ollama first:${NC}"
    echo -e "${YELLOW}Visit https://ollama.com/download for installation instructions.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Ollama is installed.${NC}"

# Check if Ollama service is running
echo -e "${BLUE}Checking if Ollama service is running...${NC}"
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "${YELLOW}Ollama service is not running. Starting Ollama...${NC}"
    # Start Ollama in the background
    ollama serve > /dev/null 2>&1 &
    # Wait for Ollama to start up
    sleep 3
    echo -e "${GREEN}✓ Ollama service started.${NC}"
    # Set the flag to indicate we started Ollama
    OLLAMA_WAS_STARTED_BY_SCRIPT=true
else
    echo -e "${GREEN}✓ Ollama service is already running.${NC}"
fi

# Check if selected model is available, and download if needed
echo -e "${BLUE}Checking for ${MODEL_NAME} model...${NC}"
if ! ollama list | grep -q "${MODEL_NAME}"; then
    # Use the new download function with progress bar
    download_model_with_progress "${MODEL_NAME}"
else
    echo -e "${GREEN}✓ ${MODEL_NAME} model is already available.${NC}"
fi

# Check for required Python packages
echo -e "${BLUE}Checking Python environment...${NC}"
if ! command_exists python3; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3 first.${NC}"
    exit 1
fi

# Check if virtual environment exists and activate it if it does
if [ -d ".venv" ]; then
    echo -e "${BLUE}Activating virtual environment...${NC}"
    source .venv/bin/activate
else
    echo -e "${YELLOW}No virtual environment found. Creating one...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment created and activated.${NC}"
fi

# Install required packages if needed
echo -e "${BLUE}Checking required packages...${NC}"
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Required packages are installed.${NC}"

# Start the application
echo -e "${BLUE}Starting Clara AI with model: ${BOLD}${MODEL_NAME}${NC}${BLUE}...${NC}"
echo -e "${BOLD}Press Ctrl+C to stop the application${NC}"
echo

# Build the command with all arguments
CMD_ARGS="--model ${MODEL_NAME}"

# Add any other arguments passed to the script
if [ ${#APP_ARGS[@]} -gt 0 ]; then
    for arg in "${APP_ARGS[@]}"; do
        CMD_ARGS="${CMD_ARGS} ${arg}"
    done
fi

# Add quiet mode by default to prevent double logging
if [[ ! "${CMD_ARGS}" =~ "--quiet" ]]; then
    CMD_ARGS="${CMD_ARGS} --quiet"
fi

# Run the application directly (this is more reliable than using an inline Python script)
python3 main.py ${CMD_ARGS}

# Note: The cleanup function will handle deactivation and Ollama shutdown via the trap