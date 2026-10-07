# DevTrackr Setup Script for Windows
# Automates the complete development environment setup

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Blue
}

# Check if command exists
function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

# Check Python version
function Test-Python {
    Write-Step "Checking Python installation..."

    if (-not (Test-Command "python")) {
        Write-Error "Python is not installed or not in PATH"
        Write-Host "Please install Python 3.11 or higher from https://www.python.org/"
        exit 1
    }

    $pythonVersion = python --version 2>&1
    $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"

    if (-not $versionMatch) {
        Write-Error "Could not determine Python version"
        exit 1
    }

    $major = [int]$matches[1]
    $minor = [int]$matches[2]

    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Error "Python 3.11 or higher is required. Found: $pythonVersion"
        exit 1
    }

    Write-Success "Python $pythonVersion found"
}

# Check Docker
function Test-Docker {
    Write-Step "Checking Docker installation..."

    if (-not (Test-Command "docker")) {
        Write-Error "Docker is not installed"
        Write-Host "Please install Docker Desktop from https://www.docker.com/get-started"
        exit 1
    }

    try {
        docker info | Out-Null
        Write-Success "Docker is installed and running"
    } catch {
        Write-Error "Docker is not running"
        Write-Host "Please start Docker Desktop"
        exit 1
    }
}

# Check Docker Compose
function Test-DockerCompose {
    Write-Step "Checking Docker Compose..."

    # Try docker compose (newer) first, then docker-compose (older)
    $dockerComposeCmd = $null

    try {
        docker compose version | Out-Null
        $script:DockerComposeCmd = "docker compose"
        Write-Success "Docker Compose (plugin) found"
    } catch {
        if (Test-Command "docker-compose") {
            $script:DockerComposeCmd = "docker-compose"
            Write-Success "Docker Compose (standalone) found"
        } else {
            Write-Error "Docker Compose is not installed"
            Write-Host "Please install Docker Compose"
            exit 1
        }
    }
}

# Check Git
function Test-Git {
    Write-Step "Checking Git installation..."

    if (-not (Test-Command "git")) {
        Write-Warning "Git is not installed (optional but recommended)"
    } else {
        Write-Success "Git is installed"
    }
}

# Create virtual environment
function Initialize-Venv {
    Write-Step "Setting up Python virtual environment..."

    if (Test-Path "venv") {
        Write-Info "Virtual environment already exists, skipping creation"
    } else {
        python -m venv venv
        Write-Success "Virtual environment created"
    }

    # Activate virtual environment
    & "venv\Scripts\Activate.ps1"
    Write-Success "Virtual environment activated"
}

# Install dependencies
function Install-Dependencies {
    Write-Step "Installing Python dependencies..."

    # Upgrade pip
    python -m pip install --upgrade pip --quiet
    Write-Success "pip upgraded"

    # Install requirements
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt --quiet
        Write-Success "Dependencies installed"
    } else {
        Write-Error "requirements.txt not found"
        exit 1
    }

    # Verify critical packages
    try {
        python -c "import fastapi, sqlalchemy, alembic" 2>&1 | Out-Null
        Write-Success "Critical packages verified"
    } catch {
        Write-Error "Critical packages verification failed"
        exit 1
    }
}

# Start database
function Start-Database {
    Write-Step "Starting PostgreSQL database..."

    # Check if container is already running
    $containerRunning = docker ps --format '{{.Names}}' | Select-String -Pattern "^devtrackr-db$"

    if ($containerRunning) {
        Write-Info "Database container is already running"
    } else {
        # Start database
        Invoke-Expression "$DockerComposeCmd up -d db"
        Write-Success "Database container started"

        # Wait for database to be healthy
        Write-Info "Waiting for database to be ready..."
        $maxAttempts = 30
        $attempt = 0
        $ready = $false

        while ($attempt -lt $maxAttempts -and -not $ready) {
            try {
                docker exec devtrackr-db pg_isready -U dev -d devtrackr 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    $ready = $true
                    Write-Success "Database is ready"
                }
            } catch {
                # Continue waiting
            }

            if (-not $ready) {
                $attempt++
                Start-Sleep -Seconds 1
            }
        }

        if (-not $ready) {
            Write-Error "Database failed to become ready after $maxAttempts seconds"
            exit 1
        }
    }
}

# Run migrations
function Invoke-Migrations {
    Write-Step "Running database migrations..."

    try {
        python -m alembic upgrade head
        Write-Success "Database migrations completed"
    } catch {
        Write-Error "Database migrations failed"
        Write-Host "Please check the error messages above"
        exit 1
    }
}

# Check health endpoint
function Test-Health {
    Write-Step "Verifying API health..."

    # Check if port 8000 is already in use
    $portInUse = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue

    if ($portInUse) {
        Write-Warning "Port 8000 is already in use"
        Write-Info "Assuming server is already running, testing health endpoint..."
    } else {
        Write-Info "Starting server in background for health check..."

        # Start server in background
        $job = Start-Job -ScriptBlock {
            Set-Location $using:PWD
            & "venv\Scripts\python.exe" -m uvicorn src.main:app --host 0.0.0.0 --port 8000
        }

        # Wait for server to start
        $maxAttempts = 15
        $attempt = 0
        $healthy = $false

        while ($attempt -lt $maxAttempts -and -not $healthy) {
            Start-Sleep -Seconds 1
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    $healthy = $true
                    Write-Success "Server is responding"
                }
            } catch {
                # Continue waiting
            }
            $attempt++
        }

        # Stop background job
        Stop-Job $job -ErrorAction SilentlyContinue
        Remove-Job $job -ErrorAction SilentlyContinue

        if (-not $healthy) {
            Write-Warning "Could not verify server health (server may need to be started manually)"
            return
        }
    }

    # Test health endpoint
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Success "API health check passed"
        }
    } catch {
        Write-Warning "API health check failed (server may need to be started manually)"
    }
}

# Main execution
function Main {
    Write-Host "`n"
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║     DevTrackr Setup Script             ║" -ForegroundColor Cyan
    Write-Host "║     Automated Environment Setup        ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""

    # Run all checks and setup steps
    Test-Python
    Test-Docker
    Test-DockerCompose
    Test-Git
    Initialize-Venv
    Install-Dependencies
    Start-Database
    Invoke-Migrations
    Test-Health

    # Success message
    Write-Host "`n"
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  Setup completed successfully!          ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "  1. Activate the virtual environment:"
    Write-Host "     " -NoNewline
    Write-Host "venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  2. Start the development server:"
    Write-Host "     " -NoNewline
    Write-Host "uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  3. Access the API documentation:"
    Write-Host "     " -NoNewline
    Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Success "Happy coding! 🚀"
}

# Run main function
Main
