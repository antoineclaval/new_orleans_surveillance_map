#!/bin/bash
# NOLA Camera Mapping - Setup Script
#
# Development Modes:
#   ./scripts/setup.sh local    # Recommended: Local venv + containerized DB
#   ./scripts/setup.sh dev      # Full containerized development stack
#   ./scripts/setup.sh prod     # Production deployment
#
# Server Setup:
#   ./scripts/setup.sh prepare-prod  # Full VPS setup (resumable, checkpointed)
#
# See README.md for detailed documentation.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# State file for prepare_prod checkpointing
PREPARE_STATE_FILE="$PROJECT_ROOT/.prepare_prod_state"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# =============================================================================
# Dependency Checks
# =============================================================================

check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "UV is not installed. Please install it first:"
        echo ""
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo ""
        echo "  Or on Fedora: sudo dnf install uv"
        echo ""
        exit 1
    fi
    print_status "UV found: $(uv --version)"
}

check_podman() {
    if ! command -v podman &> /dev/null; then
        print_error "Podman is not installed. Please install Podman first."
        echo ""
        echo "  On Fedora: sudo dnf install podman"
        echo "  On Ubuntu: sudo apt install podman"
        echo ""
        exit 1
    fi
    print_status "Podman found"
}

check_podman_compose() {
    if ! command -v podman-compose &> /dev/null; then
        print_error "podman-compose not found. Please install it first:"
        echo ""
        echo "  On Fedora:  sudo dnf install podman-compose"
        echo "  On Ubuntu:  sudo apt install podman-compose"
        echo "  Via uv:     uv tool install podman-compose"
        echo "  Via pip:    pip3 install --user podman-compose"
        echo ""
        exit 1
    fi
    print_status "podman-compose found"
}

check_system_deps() {
    # Check for GeoDjango system dependencies
    local missing_deps=()

    if ! command -v gdal-config &> /dev/null && ! [ -f /usr/include/gdal.h ]; then
        missing_deps+=("gdal")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_warning "Some GeoDjango dependencies may be missing: ${missing_deps[*]}"
        echo ""
        echo "  On Fedora: sudo dnf install gdal gdal-devel geos geos-devel proj proj-devel"
        echo "  On Ubuntu: sudo apt install gdal-bin libgdal-dev libgeos-dev libproj-dev"
        echo ""
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# =============================================================================
# Environment Setup
# =============================================================================

generate_secret_key() {
    python3 -c "import secrets; print(secrets.token_urlsafe(50))"
}

create_env_file() {
    if [ ! -f ".env" ]; then
        print_status "Creating .env file..."
        cat > .env << EOF
# NOLA Camera Mapping Environment Variables
# Generated on $(date)

# =============================================================================
# Django Settings
# =============================================================================
DJANGO_SECRET_KEY=$(generate_secret_key)
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
DJANGO_DEBUG=True

# =============================================================================
# Database Settings
# =============================================================================
POSTGRES_DB=nola_cameras
POSTGRES_USER=nola
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)

# For containerized DB (used by 'local' and 'dev' modes)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# =============================================================================
# Production Settings (change these for production deployment)
# =============================================================================
# DOMAIN=yourdomain.com
# DJANGO_ALLOWED_HOSTS=yourdomain.com
# CSRF_TRUSTED_ORIGINS=https://yourdomain.com
# DJANGO_DEBUG=False
EOF
        print_status ".env file created with secure passwords"
    else
        print_warning ".env file already exists, skipping creation"
    fi
}

load_env() {
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi
}

# =============================================================================
# Local Development (venv + containerized DB)
# =============================================================================

start_local() {
    print_header "Local Development Setup"

    echo "This mode uses:"
    echo "  • Local Python virtual environment (managed by UV)"
    echo "  • Containerized PostgreSQL/PostGIS database"
    echo "  • Django development server running directly on your machine"
    echo ""

    check_uv
    check_podman
    check_podman_compose
    check_system_deps
    create_env_file
    load_env

    # Create/sync virtual environment
    print_status "Creating virtual environment and installing dependencies..."
    uv sync --dev

    # Start database container
    print_status "Starting PostgreSQL/PostGIS container..."
    podman-compose -f containers/podman-compose.yml up -d db

    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    sleep 3

    local retries=30
    while ! podman exec nola-db pg_isready -U "${POSTGRES_USER:-nola}" -d "${POSTGRES_DB:-nola_cameras}" &> /dev/null; do
        retries=$((retries - 1))
        if [ $retries -eq 0 ]; then
            print_error "Database failed to start. Check: podman logs nola-db"
            exit 1
        fi
        sleep 1
    done
    print_status "Database is ready"

    # Run migrations
    print_status "Running database migrations..."
    uv run python nola_cameras/manage.py migrate

    print_header "Local Development Ready!"

    echo "Database is running in container 'nola-db'"
    echo ""
    echo -e "${GREEN}To start the Django development server:${NC}"
    echo ""
    echo "  cd nola_cameras"
    echo "  uv run python manage.py runserver"
    echo ""
    echo -e "${GREEN}Or use the shortcut:${NC}"
    echo ""
    echo "  ./scripts/setup.sh run"
    echo ""
    echo -e "${GREEN}Other useful commands:${NC}"
    echo ""
    echo "  ./scripts/setup.sh shell      # Django shell"
    echo "  ./scripts/setup.sh superuser  # Create admin user"
    echo "  ./scripts/setup.sh seed       # Load sample data"
    echo "  ./scripts/setup.sh db-stop    # Stop database container"
    echo ""
    echo "Access the app at: http://localhost:8000"
    echo "Admin interface:   http://localhost:8000/admin/"
    echo ""
}

run_server() {
    load_env

    # Check if DB is running
    if ! podman ps | grep -q nola-db; then
        print_warning "Database container not running. Starting it..."
        podman-compose -f containers/podman-compose.yml up -d db
        sleep 3
    fi

    print_status "Starting Django development server..."
    cd nola_cameras
    exec uv run python manage.py runserver
}

run_shell() {
    load_env
    cd nola_cameras
    exec uv run python manage.py shell
}

stop_db() {
    print_status "Stopping database container..."
    podman stop nola-db 2>/dev/null || true
    print_status "Database container stopped"
}

# =============================================================================
# Containerized Development (full Docker-like setup)
# =============================================================================

start_dev() {
    print_header "Containerized Development Setup"

    echo "This mode runs everything in containers:"
    echo "  • Django application in container"
    echo "  • PostgreSQL/PostGIS in container"
    echo "  • Code mounted as volume for hot reload"
    echo ""

    check_podman
    create_env_file
    load_env

    # Create shared network if it doesn't exist
    if ! podman network exists nola-net 2>/dev/null; then
        print_status "Creating container network..."
        podman network create nola-net
    fi

    # Start DB container (create if first run, start if stopped)
    if podman ps -a --format '{{.Names}}' | grep -q '^nola-db$'; then
        print_status "Starting existing database container..."
        podman start nola-db
    else
        print_status "Starting PostgreSQL/PostGIS container..."
        podman run -d \
            --name nola-db \
            --network nola-net \
            -e POSTGRES_DB="${POSTGRES_DB:-nola_cameras}" \
            -e POSTGRES_USER="${POSTGRES_USER:-nola}" \
            -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-nola_dev_password}" \
            -v nola_postgres_data:/var/lib/postgresql/data \
            -p 5432:5432 \
            docker.io/postgis/postgis:16-3.4
    fi

    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    local retries=30
    while ! podman exec nola-db pg_isready -U "${POSTGRES_USER:-nola}" -d "${POSTGRES_DB:-nola_cameras}" &>/dev/null; do
        retries=$((retries - 1))
        if [ $retries -eq 0 ]; then
            print_error "Database failed to start. Check: podman logs nola-db"
            exit 1
        fi
        sleep 2
    done
    print_status "Database is ready"

    # Build the dev image
    print_status "Building development image..."
    podman build -f containers/Containerfile.dev -t nola-web-dev .

    # Remove any stopped web container before starting fresh
    podman rm -f nola-web-dev 2>/dev/null || true

    # Start Django dev server (attached so logs stream to terminal; Ctrl+C to stop)
    print_status "Starting Django development server..."
    print_info "Access the app at: http://localhost:8000"
    print_info "Press Ctrl+C to stop"
    echo ""
    podman run --rm -it \
        --name nola-web-dev \
        --network nola-net \
        -e DJANGO_SETTINGS_MODULE=config.settings.development \
        -e POSTGRES_HOST=nola-db \
        -e POSTGRES_DB="${POSTGRES_DB:-nola_cameras}" \
        -e POSTGRES_USER="${POSTGRES_USER:-nola}" \
        -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-nola_dev_password}" \
        -e POSTGRES_PORT=5432 \
        -e DJANGO_DEBUG=True \
        -v "$(pwd)/nola_cameras:/app:z" \
        -p 8000:8000 \
        nola-web-dev \
        sh -c "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
}

container_shell() {
    print_header "Container Shell"

    check_podman
    load_env

    # If the web-dev container is already running, exec straight into it
    if podman ps --format '{{.Names}}' | grep -q '^nola-web-dev$'; then
        print_status "Attaching to running nola-web-dev container..."
        exec podman exec -it nola-web-dev sh
    fi

    # Otherwise ensure the network and DB are up, then start a fresh container
    if ! podman network exists nola-net 2>/dev/null; then
        print_status "Creating container network..."
        podman network create nola-net
    fi

    if podman ps -a --format '{{.Names}}' | grep -q '^nola-db$'; then
        podman start nola-db 2>/dev/null || true
    else
        print_status "Starting PostgreSQL/PostGIS container..."
        podman run -d \
            --name nola-db \
            --network nola-net \
            -e POSTGRES_DB="${POSTGRES_DB:-nola_cameras}" \
            -e POSTGRES_USER="${POSTGRES_USER:-nola}" \
            -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-nola_dev_password}" \
            -v nola_postgres_data:/var/lib/postgresql/data \
            -p 5432:5432 \
            docker.io/postgis/postgis:16-3.4
    fi

    print_status "Waiting for database to be ready..."
    local retries=30
    while ! podman exec nola-db pg_isready -U "${POSTGRES_USER:-nola}" -d "${POSTGRES_DB:-nola_cameras}" &>/dev/null; do
        retries=$((retries - 1))
        if [ $retries -eq 0 ]; then
            print_error "Database failed to start. Check: podman logs nola-db"
            exit 1
        fi
        sleep 2
    done
    print_status "Database is ready"

    print_status "Building development image..."
    podman build -f containers/Containerfile.dev -t nola-web-dev .

    print_status "Launching shell inside container (code mounted at /app)..."
    print_info "Run 'python manage.py makemigrations' etc. from here"
    echo ""
    exec podman run --rm -it \
        --name nola-web-dev \
        --network nola-net \
        -e DJANGO_SETTINGS_MODULE=config.settings.development \
        -e POSTGRES_HOST=nola-db \
        -e POSTGRES_DB="${POSTGRES_DB:-nola_cameras}" \
        -e POSTGRES_USER="${POSTGRES_USER:-nola}" \
        -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-nola_dev_password}" \
        -e POSTGRES_PORT=5432 \
        -e DJANGO_DEBUG=True \
        -v "$(pwd)/nola_cameras:/app:z" \
        nola-web-dev \
        sh
}

# =============================================================================
# Production Deployment
# =============================================================================

start_prod() {
    print_header "Production Deployment"

    check_podman
    check_podman_compose

    if [ ! -f ".env" ]; then
        print_error ".env file not found. Please create it first."
        exit 1
    fi

    load_env

    # Verify required production variables
    if [ -z "$DJANGO_SECRET_KEY" ]; then
        print_error "DJANGO_SECRET_KEY is not set in .env"
        exit 1
    fi

    # Update POSTGRES_HOST for containerized mode
    export POSTGRES_HOST=db

    # Tear down any existing stack so podman-compose always creates fresh containers
    # on the correct network. Use 'down' (not manual rm) so it respects --requires
    # dependency order: caddy → web → db.
    print_status "Tearing down any existing stack..."
    podman-compose -f containers/podman-compose.yml down 2>/dev/null || true

    print_status "Building and starting production containers..."
    podman-compose -f containers/podman-compose.yml up -d --build db web caddy

    # Wait for DB to be healthy before migrating
    print_status "Waiting for database to be ready..."
    local waited=0
    until podman exec nola-db pg_isready -U "${POSTGRES_USER:-nola}" -d "${POSTGRES_DB:-nola_cameras}" &>/dev/null; do
        if [ $waited -ge 60 ]; then
            print_error "Database did not become ready after 60s. Check: podman logs nola-db"
            exit 1
        fi
        sleep 2
        waited=$((waited + 2))
    done
    print_status "Database is ready"

    # Run migrations
    print_status "Running database migrations..."
    podman exec nola-web python manage.py migrate

    print_status "Production server running!"
    print_status "Access at https://${DOMAIN:-localhost}"
}

# =============================================================================
# Production Update
# =============================================================================

update_prod() {
    print_header "Production Update"

    check_podman
    check_podman_compose

    if [ ! -f ".env" ]; then
        print_error ".env file not found."
        exit 1
    fi

    load_env
    export POSTGRES_HOST=db

    print_status "Pulling latest code..."
    git pull

    print_status "Rebuilding and restarting containers (DB volume preserved)..."
    podman-compose -f containers/podman-compose.yml down 2>/dev/null || true
    podman-compose -f containers/podman-compose.yml up -d --build db web caddy

    # Wait for DB
    print_status "Waiting for database to be ready..."
    local waited=0
    until podman exec nola-db pg_isready -U "${POSTGRES_USER:-nola}" -d "${POSTGRES_DB:-nola_cameras}" &>/dev/null; do
        if [ $waited -ge 60 ]; then
            print_error "Database did not become ready after 60s. Check: podman logs nola-db"
            exit 1
        fi
        sleep 2
        waited=$((waited + 2))
    done

    print_status "Running database migrations..."
    podman exec nola-web python manage.py migrate

    print_status "Update complete — app running at http://${DOMAIN:-localhost}"
}

# =============================================================================
# Database & Django Management Commands
# =============================================================================

run_migrations() {
    print_status "Running database migrations..."
    load_env

    if podman ps | grep -q nola-web-dev; then
        podman exec nola-web-dev python manage.py migrate
    elif podman ps | grep -q nola-web; then
        podman exec nola-web python manage.py migrate
    elif [ -d ".venv" ]; then
        cd nola_cameras
        uv run python manage.py migrate
    else
        print_error "No running environment found. Start with 'local', 'dev', or 'prod' first."
        exit 1
    fi

    print_status "Migrations completed"
}

make_migrations() {
    local app="${2:-}"
    print_status "Making migrations${app:+ for $app}..."
    load_env

    if podman ps | grep -q nola-web-dev; then
        podman exec nola-web-dev python manage.py makemigrations $app
    elif podman ps | grep -q nola-web; then
        podman exec nola-web python manage.py makemigrations $app
    elif [ -d ".venv" ]; then
        cd nola_cameras
        uv run python manage.py makemigrations $app
    else
        print_error "No running environment found. Start with 'local', 'dev', or 'prod' first."
        exit 1
    fi

    print_status "Makemigrations completed"
}

seed_database() {
    print_status "Seeding database with sample data..."
    load_env

    if podman ps | grep -q nola-web-dev; then
        podman exec -i nola-web-dev python manage.py shell < scripts/seed_data.py
    elif podman ps | grep -q nola-web; then
        podman exec -i nola-web python manage.py shell < scripts/seed_data.py
    elif [ -d ".venv" ]; then
        cd nola_cameras
        uv run python manage.py shell < ../scripts/seed_data.py
    else
        print_error "No running environment found. Start with 'local' or 'dev' first."
        exit 1
    fi

    print_status "Database seeded successfully"
}

create_superuser() {
    print_status "Creating superuser..."
    load_env

    if podman ps | grep -q nola-web-dev; then
        podman exec -it nola-web-dev python manage.py createsuperuser
    elif podman ps | grep -q nola-web; then
        podman exec -it nola-web python manage.py createsuperuser
    elif [ -d ".venv" ]; then
        cd nola_cameras
        uv run python manage.py createsuperuser
    else
        print_error "No running environment found. Start with 'local' or 'dev' first."
        exit 1
    fi
}

# =============================================================================
# Cleanup Commands
# =============================================================================

stop_all() {
    print_status "Stopping all containers..."
    podman stop nola-web-dev nola-web nola-caddy nola-db 2>/dev/null || true
    podman rm nola-web-dev nola-web nola-caddy 2>/dev/null || true
    print_status "All containers stopped"
}

clean_all() {
    print_warning "This will remove all containers, volumes, and the virtual environment."
    read -p "Are you sure? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleaning up..."
        podman rm -f nola-web-dev nola-web nola-caddy nola-db 2>/dev/null || true
        podman volume rm nola_postgres_data nola_media_data nola_static_data 2>/dev/null || true
        podman network rm nola-net 2>/dev/null || true
        rm -rf .venv
        print_status "Cleanup complete"
    fi
}

# =============================================================================
# prepare_prod — Checkpoint Helpers
# =============================================================================

prep_step_done() { [ -f "$PREPARE_STATE_FILE" ] && grep -qxF "$1" "$PREPARE_STATE_FILE"; }
prep_mark_done() { echo "$1" >> "$PREPARE_STATE_FILE"; }

run_prep_step() {
    local num="$1" total="$2" step_id="$3" step_desc="$4" step_fn="$5"
    if prep_step_done "$step_id"; then
        print_info "[$num/$total] $step_desc — already done, skipping"
        return 0
    fi
    echo ""
    echo -e "${BLUE}━━━ [$num/$total] $step_desc ━━━${NC}"
    echo ""
    "$step_fn"
    prep_mark_done "$step_id"
    print_status "[$num/$total] $step_desc — done"
}

# =============================================================================
# prepare_prod — Step Functions
# =============================================================================

prep_step_system_deps() {
    if [ "$(id -u)" -ne 0 ]; then
        print_error "This step requires root. Re-run as root or with sudo."
        exit 1
    fi
    apt-get update -y
    apt-get upgrade -y
    apt-get install -y git podman podman-compose
}

prep_step_firewall() {
    if [ "$(id -u)" -ne 0 ]; then
        print_error "This step requires root. Re-run as root or with sudo."
        exit 1
    fi
    ufw allow OpenSSH
    ufw allow 80
    ufw allow 443
    ufw --force enable
    print_status "Firewall configured: SSH, HTTP, HTTPS allowed"
}

prep_step_ssh_harden() {
    if [ "$(id -u)" -ne 0 ]; then
        print_error "This step requires root."
        exit 1
    fi

    print_warning "SSH hardening will:"
    echo "  • Disable password-based root login (key-based root stays active)"
    echo "  • Disable password authentication for all users"
    echo "  • Limit auth attempts to 3, idle timeout 10 min"
    echo ""
    print_warning "PREREQUISITE: Your SSH public key must already be in /root/.ssh/authorized_keys"
    print_warning "Open a second terminal and test 'ssh root@<server>' with your key BEFORE continuing."
    echo ""
    read -rp "I have confirmed key-based SSH access works. Press Enter to apply hardening... "

    cat > /etc/ssh/sshd_config.d/99-hardening.conf << 'EOF'
# New Orleans Camera Mapping — SSH Hardening
# Applied by scripts/setup.sh prepare-prod
# To revert: rm /etc/ssh/sshd_config.d/99-hardening.conf && systemctl restart ssh

# Allow root only via key, not password (Hetzner default user is root)
PermitRootLogin prohibit-password

# No password auth anywhere
PasswordAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no

# Rate-limit attempts and idle connections
MaxAuthTries 3
MaxSessions 5
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

    # Validate config before restarting
    sshd -t || {
        print_error "sshd config validation failed — reverting"
        rm -f /etc/ssh/sshd_config.d/99-hardening.conf
        exit 1
    }

    systemctl restart ssh
    print_status "SSH hardened. Key-based auth only. Password login disabled."
}

prep_step_fail2ban() {
    if [ "$(id -u)" -ne 0 ]; then
        print_error "This step requires root."
        exit 1
    fi

    apt-get install -y fail2ban

    # jail.local overrides defaults; don't touch jail.conf (wiped on upgrades)
    cat > /etc/fail2ban/jail.d/nola.local << 'EOF'
# NOLA Camera Mapping — fail2ban jails
# Applied by scripts/setup.sh prepare-prod

[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled  = true
port     = ssh
maxretry = 3
EOF

    systemctl enable fail2ban
    systemctl restart fail2ban
    print_status "fail2ban enabled — SSH jail active (ban after 3 attempts / 1h)"
    print_info "Check status anytime: fail2ban-client status sshd"
}

prep_step_sysctl_harden() {
    if [ "$(id -u)" -ne 0 ]; then
        print_error "This step requires root."
        exit 1
    fi

    cat > /etc/sysctl.d/99-nola-hardening.conf << 'EOF'
# NOLA Camera Mapping — Kernel Hardening
# Applied by scripts/setup.sh prepare-prod

# NOTE: ip_forward left enabled — required for podman bridge networking
net.ipv4.ip_forward = 1

# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2

# ICMP hardening
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Disable ICMP redirects (not a router)
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0

# Source routing (used in spoofing attacks)
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# Reverse path filtering (anti-spoofing)
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Log martians (packets with impossible source addresses)
net.ipv4.conf.all.log_martians = 1
EOF

    sysctl --system > /dev/null
    print_status "Kernel hardening applied (/etc/sysctl.d/99-nola-hardening.conf)"
}

prep_step_auto_updates() {
    if [ "$(id -u)" -ne 0 ]; then
        print_error "This step requires root."
        exit 1
    fi

    apt-get install -y unattended-upgrades

    # 20auto-upgrades: enable daily security update downloads and installs
    cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF

    # Disable auto-reboot — containers don't survive host reboots without restart policies
    # Operators should reboot manually during maintenance windows
    if [ -f /etc/apt/apt.conf.d/50unattended-upgrades ]; then
        sed -i 's|//Unattended-Upgrade::Automatic-Reboot ".*";|Unattended-Upgrade::Automatic-Reboot "false";|' \
            /etc/apt/apt.conf.d/50unattended-upgrades
        sed -i 's|Unattended-Upgrade::Automatic-Reboot "true";|Unattended-Upgrade::Automatic-Reboot "false";|' \
            /etc/apt/apt.conf.d/50unattended-upgrades
    fi

    systemctl enable unattended-upgrades
    systemctl restart unattended-upgrades
    print_status "Automatic security updates enabled (no auto-reboot)"
    print_info "Reboot manually after kernel updates: sudo reboot"
}

prep_step_env() {
    create_env_file
    echo ""
    print_info "Edit .env now — set the following production values:"
    echo "  DOMAIN=yourdomain.com"
    echo "  DJANGO_ALLOWED_HOSTS=yourdomain.com"
    echo "  CSRF_TRUSTED_ORIGINS=https://yourdomain.com"
    echo "  DJANGO_DEBUG=False"
    echo "  (DJANGO_SECRET_KEY and POSTGRES_PASSWORD are already generated)"
    echo ""
    read -rp "Press Enter when .env is ready to continue... "
}

prep_step_validate_env() {
    load_env

    local ok=1

    if [ -z "$DJANGO_SECRET_KEY" ]; then
        print_error "DJANGO_SECRET_KEY is not set in .env"
        ok=0
    fi

    if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "yourdomain.com" ]; then
        print_error "DOMAIN is not set or still set to 'yourdomain.com' in .env"
        ok=0
    fi

    if [ "$DJANGO_DEBUG" != "False" ]; then
        print_error "DJANGO_DEBUG must be 'False' in .env for production (got: '${DJANGO_DEBUG}')"
        ok=0
    fi

    if [ -z "$POSTGRES_PASSWORD" ]; then
        print_error "POSTGRES_PASSWORD is not set in .env"
        ok=0
    fi

    if [ "$ok" -eq 0 ]; then
        print_error "Fix the above issues in .env, then re-run: ./scripts/setup.sh prepare-prod"
        exit 1
    fi

    print_status "All required environment variables look good"
}

prep_step_dns() {
    load_env

    # If DOMAIN is a bare IPv4 or IPv6 address, skip DNS verification entirely
    if [[ "$DOMAIN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || [[ "$DOMAIN" =~ ^[0-9a-fA-F:]+$ ]]; then
        print_status "DOMAIN is an IP address — skipping DNS check"
        return 0
    fi

    local public_ip
    public_ip="$(curl -sf https://ifconfig.me)" || {
        print_error "Could not determine server public IP (curl ifconfig.me failed)"
        exit 1
    }

    local resolved_ip
    resolved_ip="$(getent hosts "$DOMAIN" | awk '{ print $1 }' | head -1)" || true

    if [ -z "$resolved_ip" ]; then
        print_error "DNS: '$DOMAIN' does not resolve to any IP address."
        print_error "Point an A record for '$DOMAIN' to this server's IP: $public_ip"
        exit 1
    fi

    if [ "$resolved_ip" != "$public_ip" ]; then
        print_error "DNS mismatch: '$DOMAIN' resolves to $resolved_ip but this server's IP is $public_ip"
        print_error "Update the A record for '$DOMAIN' to point to $public_ip"
        exit 1
    fi

    print_status "DNS OK: $DOMAIN → $public_ip"
}

prep_step_deploy() {
    start_prod
}

prep_step_systemd() {
    if [ "$(id -u)" -ne 0 ]; then
        print_error "This step requires root. Re-run as root or with sudo."
        exit 1
    fi

    local compose_bin
    compose_bin="$(command -v podman-compose)" || {
        print_error "podman-compose not found in PATH"
        exit 1
    }

    cat > /etc/systemd/system/nola-cameras.service << EOF
[Unit]
Description=NOLA Camera Mapping
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_ROOT
ExecStart=$compose_bin -f containers/podman-compose.yml up -d db web caddy
ExecStop=$compose_bin -f containers/podman-compose.yml down
EnvironmentFile=$PROJECT_ROOT/.env

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable nola-cameras.service
    print_status "systemd service installed and enabled: nola-cameras.service"
}

prep_step_verify() {
    load_env

    print_info "Running containers:"
    podman ps

    echo ""
    print_info "Waiting for https://$DOMAIN/ to respond (up to 60s — TLS cert may still be provisioning)..."

    local i=0
    while [ $i -lt 12 ]; do
        if curl -sf "https://$DOMAIN/" > /dev/null 2>&1; then
            print_status "https://$DOMAIN/ is responding — deployment verified!"
            return 0
        fi
        i=$((i + 1))
        echo "  Attempt $i/12 — not ready yet, waiting 5s..."
        sleep 5
    done

    print_warning "https://$DOMAIN/ did not respond after 60s."
    print_warning "This is normal if Caddy is still provisioning the TLS certificate."
    print_warning "Check again in a minute: curl -I https://$DOMAIN/"
}

# =============================================================================
# prepare_prod — Orchestrator
# =============================================================================

prepare_prod() {
    print_header "Hetzner VPS — Production Preparation"

    if [ -f "$PREPARE_STATE_FILE" ]; then
        print_info "Resuming. Completed steps:"
        while IFS= read -r s; do echo "  [✓] $s"; done < "$PREPARE_STATE_FILE"
        echo ""
    fi

    trap 'print_error "Step failed. Fix the issue above, then re-run: ./scripts/setup.sh prepare-prod"' ERR

    local steps=(
        "system_deps|Install system dependencies|prep_step_system_deps"
        "firewall|Configure firewall (ufw)|prep_step_firewall"
        "ssh_harden|Harden SSH configuration|prep_step_ssh_harden"
        "fail2ban|Install & configure fail2ban|prep_step_fail2ban"
        "sysctl_harden|Apply kernel hardening (sysctl)|prep_step_sysctl_harden"
        "auto_updates|Enable automatic security updates|prep_step_auto_updates"
        "env|Configure environment (.env)|prep_step_env"
        "validate_env|Validate environment variables|prep_step_validate_env"
        "dns|Verify DNS resolution|prep_step_dns"
        "deploy|Deploy containers|prep_step_deploy"
        "systemd|Install systemd auto-start service|prep_step_systemd"
        "verify|Verify deployment|prep_step_verify"
    )
    local total=${#steps[@]}
    local num=0
    for entry in "${steps[@]}"; do
        num=$((num + 1))
        IFS='|' read -r step_id step_desc step_fn <<< "$entry"
        run_prep_step "$num" "$total" "$step_id" "$step_desc" "$step_fn"
    done

    print_header "Production setup complete!"
    echo "  App:   https://${DOMAIN}"
    echo "  Admin: https://${DOMAIN}/admin/"
    echo ""
    echo "Next: ./scripts/setup.sh superuser"
    echo "Reset: rm $PREPARE_STATE_FILE"
}

# =============================================================================
# Help
# =============================================================================

show_help() {
    echo "NOLA Camera Mapping - Setup Script"
    echo ""
    echo -e "${BLUE}Usage:${NC} ./scripts/setup.sh [command]"
    echo ""
    echo -e "${BLUE}Development Modes:${NC}"
    echo "  local       ${GREEN}(Recommended)${NC} Local venv + containerized PostgreSQL"
    echo "              Best for: Fast iteration, IDE support, debugging"
    echo ""
    echo "  dev         Full containerized stack with hot reload"
    echo "              Best for: Testing container builds, CI/CD"
    echo ""
    echo "  prod        Production deployment with Caddy reverse proxy"
    echo "              Best for: Staging and production servers"
    echo ""
    echo -e "${BLUE}Local Development Commands:${NC}"
    echo "  run             Start Django development server (after 'local' setup)"
    echo "  shell           Open Django shell"
    echo "  container-shell Start (or attach to) the dev container and open a shell"
    echo "  db-stop         Stop the database container"
    echo ""
    echo -e "${BLUE}Database Commands:${NC}"
    echo "  makemigrations [app]  Generate new migration files"
    echo "  migrate               Run database migrations"
    echo "  seed                  Load sample camera data"
    echo "  superuser             Create Django admin superuser"
    echo ""
    echo -e "${BLUE}Server Setup Commands:${NC}"
    echo "  prepare-prod    Full VPS setup + hardening (resumable, checkpointed)"
    echo "                  Includes: SSH hardening, fail2ban, sysctl, auto-updates"
    echo "                  Re-run after fixing any failure to resume from that step"
    echo "                  Reset progress: rm .prepare_prod_state"
    echo "  update          Pull latest code and restart containers (DB data preserved)"
    echo ""
    echo -e "${BLUE}Cleanup Commands:${NC}"
    echo "  stop        Stop all running containers"
    echo "  clean       Remove containers, volumes, and venv"
    echo ""
    echo -e "${BLUE}Examples:${NC}"
    echo "  ./scripts/setup.sh local        # Set up local development"
    echo "  ./scripts/setup.sh run          # Start dev server"
    echo "  ./scripts/setup.sh seed         # Add sample cameras"
    echo "  ./scripts/setup.sh prepare-prod # Full production VPS setup"
    echo ""
}

# =============================================================================
# Main Command Handler
# =============================================================================

case "${1:-help}" in
    local)
        start_local
        ;;
    dev)
        start_dev
        ;;
    prod)
        start_prod
        ;;
    run)
        run_server
        ;;
    shell)
        run_shell
        ;;
    db-stop)
        stop_db
        ;;
    container-shell)
        container_shell
        ;;
    makemigrations)
        make_migrations "$@"
        ;;
    migrate)
        run_migrations
        ;;
    seed)
        seed_database
        ;;
    superuser)
        create_superuser
        ;;
    stop)
        stop_all
        ;;
    clean)
        clean_all
        ;;
    prepare-prod)
        prepare_prod
        ;;
    update)
        update_prod
        ;;
    help|*)
        show_help
        ;;
esac
