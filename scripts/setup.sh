#!/bin/bash

# DevTrackr Setup Script
# Automates the complete development environment setup

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    print_step "Checking Python installation..."

    if ! command_exists python3; then
        print_error "Python 3 is not installed"
        echo "Please install Python 3.11 or higher from https://www.python.org/"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        print_error "Python 3.11 or higher is required. Found: $PYTHON_VERSION"
        exit 1
    fi

    print_success "Python $PYTHON_VERSION found"
}

# Check Docker
check_docker() {
    print_step "Checking Docker installation..."

    if ! command_exists docker; then
        print_error "Docker is not installed"
        echo "Please install Docker from https://www.docker.com/get-started"
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running"
        echo "Please start Docker Desktop or Docker daemon"
        exit 1
    fi

    print_success "Docker is installed and running"
}

# Check Docker Compose
check_docker_compose() {
    print_step "Checking Docker Compose..."

    # Try docker compose (newer) first, then docker-compose (older)
    if docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
        print_success "Docker Compose (plugin) found"
    elif command_exists docker-compose; then
        DOCKER_COMPOSE_CMD="docker-compose"
        print_success "Docker Compose (standalone) found"
    else
        print_error "Docker Compose is not installed"
        echo "Please install Docker Compose"
        exit 1
    fi
}

# Check Git
check_git() {
    print_step "Checking Git installation..."

    if ! command_exists git; then
        print_warning "Git is not installed (optional but recommended)"
    else
        print_success "Git is installed"
    fi
}

# Create virtual environment
setup_venv() {
    print_step "Setting up Python virtual environment..."

    if [ -d "venv" ]; then
        print_info "Virtual environment already exists, skipping creation"
    else
        python3 -m venv venv
        print_success "Virtual environment created"
    fi

    # Activate virtual environment
    source venv/bin/activate
    print_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_step "Installing Python dependencies..."

    # Upgrade pip
    pip install --upgrade pip --quiet
    print_success "pip upgraded"

    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --quiet
        print_success "Dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi

    # Verify critical packages
    python3 -c "import fastapi, sqlalchemy, alembic" 2>/dev/null || {
        print_error "Critical packages verification failed"
        exit 1
    }
    print_success "Critical packages verified"
}

# Start database
start_database() {
    print_step "Starting PostgreSQL database..."

    # Check if container is already running
    if docker ps --format '{{.Names}}' | grep -q "^devtrackr-db$"; then
        print_info "Database container is already running"
    else
        # Start database
        $DOCKER_COMPOSE_CMD up -d db
        print_success "Database container started"

        # Wait for database to be healthy
        print_info "Waiting for database to be ready..."
        local max_attempts=30
        local attempt=0

        while [ $attempt -lt $max_attempts ]; do
            if docker exec devtrackr-db pg_isready -U dev -d devtrackr >/dev/null 2>&1; then
                print_success "Database is ready"
                return 0
            fi
            attempt=$((attempt + 1))
            sleep 1
        done

        print_error "Database failed to become ready after ${max_attempts} seconds"
        exit 1
    fi
}

# Run migrations
run_migrations() {
    print_step "Running database migrations..."

    if python3 -m alembic upgrade head; then
        print_success "Database migrations completed"
    else
        print_error "Database migrations failed"
        echo "Please check the error messages above"
        exit 1
    fi
}

# Check health endpoint
check_health() {
    print_step "Verifying API health..."

    # Check if port 8000 is already in use
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -an 2>/dev/null | grep -q ":8000.*LISTEN"; then
        print_warning "Port 8000 is already in use"
        print_info "Assuming server is already running, testing health endpoint..."
    else
        print_info "Starting server in background for health check..."
        # Start server in background
        source venv/bin/activate
        nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
        SERVER_PID=$!

        # Wait for server to start
        local max_attempts=15
        local attempt=0

        while [ $attempt -lt $max_attempts ]; do
            if curl -s http://localhost:8000/health >/dev/null 2>&1; then
                print_success "Server is responding"
                # Kill background server
                kill $SERVER_PID 2>/dev/null || true
                wait $SERVER_PID 2>/dev/null || true
                return 0
            fi
            attempt=$((attempt + 1))
            sleep 1
        done

        print_warning "Could not verify server health (server may need to be started manually)"
        kill $SERVER_PID 2>/dev/null || true
        return 1
    fi

    # Test health endpoint
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        print_success "API health check passed"
    else
        print_warning "API health check failed (server may need to be started manually)"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════╗"
    echo "║     DevTrackr Setup Script             ║"
    echo "║     Automated Environment Setup        ║"
    echo "╚════════════════════════════════════════╝"
    echo -e "${NC}"

    # Run all checks and setup steps
    check_python
    check_docker
    check_docker_compose
    check_git
    setup_venv
    install_dependencies
    start_database
    run_migrations
    check_health

    # Success message
    echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Setup completed successfully!          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    print_info "Next steps:"
    echo "  1. Activate the virtual environment:"
    echo "     ${BLUE}source venv/bin/activate${NC}"
    echo ""
    echo "  2. Start the development server:"
    echo "     ${BLUE}uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload${NC}"
    echo ""
    echo "  3. Access the API documentation:"
    echo "     ${BLUE}http://localhost:8000/docs${NC}"
    echo ""
    print_success "Happy coding! 🚀"
}

# Run main function
main
