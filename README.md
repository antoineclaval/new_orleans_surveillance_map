# New Orleans surveillance mapping

A web application to map surveillance cameras in New Orleans with three user types:
- **Read-only viewers**: Browse the camera map
- **Editors**: Submit new camera sightings for review
- **Admins**: Review submissions, manage cameras (CRUD)

## Features

- Interactive map with camera locations using Leaflet.js and OpenStreetMap
- Marker clustering for better visualization at different zoom levels
- Filter cameras by facial recognition capability or private ownership
- Mobile-responsive design with bottom sheet for camera details
- Public submission form with map-based location picker
- Django admin with map widget, bulk actions, and CSV/GeoJSON export
- Containerized deployment with Podman

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.x, Django REST Framework, GeoDjango |
| Database | PostgreSQL 16 with PostGIS 3.4 |
| Frontend | Leaflet.js, Alpine.js, Tailwind CSS |
| Package Manager | [UV](https://github.com/astral-sh/uv)|
| Containers | Podman, podman-compose |
| Reverse Proxy | Caddy (production) |

---

## Development Setup

There are two ways to develop locally:

| Mode | Command | Best For |
|------|---------|----------|
| **Local** (recommended) | `./scripts/setup.sh local` | Fast iteration, IDE support, debugging |
| **Containerized** | `./scripts/setup.sh dev` | Testing containers, CI/CD consistency |

### Prerequisites

#### System Dependencies

**Fedora:**
```bash
# Required
sudo dnf install podman podman-compose

# For local development (GeoDjango dependencies)
sudo dnf install gdal gdal-devel geos geos-devel proj proj-devel

# UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: sudo dnf install uv
```

**Ubuntu/Debian:**
```bash
# Required
sudo apt install podman podman-compose

# For local development (GeoDjango dependencies)
sudo apt install gdal-bin libgdal-dev libgeos-dev libproj-dev

# UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

#### One-Time Setup

```bash
# Create a dedicated development toolbox
toolbox create project-nola-mapping

# Enter the toolbox
toolbox enter project-nola-mapping

# Inside toolbox: Install development dependencies
sudo dnf install -y \
    podman-remote \
    gdal gdal-devel \
    geos geos-devel \
    proj proj-devel \
    openssl

# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

#### Configure Podman Access

The toolbox needs to communicate with Podman on the host. Set up the remote connection:

```bash
# Inside the toolbox: Configure podman to use host's podman socket
# This allows containers started from toolbox to run on the host

# Create systemd user directory if needed (on host, not in toolbox)
# Exit toolbox first, then run:
exit
systemctl --user enable --now podman.socket

# Re-enter toolbox
toolbox enter project-nola-mapping

# Configure podman-remote to use host socket
mkdir -p ~/.config/containers
cat > ~/.config/containers/containers.conf << 'EOF'
[engine]
remote = true
EOF

# Create connection to host podman
podman system connection add host unix:///run/user/$(id -u)/podman/podman.sock
podman system connection default host

# Verify it works
podman ps
```


---

### Option 1: Local Development

This mode runs Django directly on your machine with a containerized PostgreSQL database. It provides the best developer experience with fast iteration, full IDE integration, and easy debugging.

```bash
# Clone and enter the project
git clone <repo-url>
cd project-nola-mapping

# Set up local development environment
./scripts/setup.sh local
```

This command will:
1. Check for required dependencies (UV, Podman, GeoDjango libraries)
2. Create a `.env` file with secure generated passwords
3. Create a Python virtual environment using UV
4. Install all dependencies
5. Start PostgreSQL/PostGIS in a container
6. Run database migrations

#### Start the Development Server

```bash
./scripts/setup.sh run
```

Or manually:
```bash
cd nola_cameras
uv run python manage.py runserver
```

#### Access the Application

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Map view |
| http://localhost:8000/report/ | Submit a camera |
| http://localhost:8000/admin/ | Admin interface |

#### Create an Admin User

```bash
./scripts/setup.sh superuser
```

#### Load Sample Data

```bash
./scripts/setup.sh seed
```

This adds 13 sample cameras around New Orleans (10 vetted, 2 pending, 1 rejected) for testing.

#### Other Useful Commands

```bash
./scripts/setup.sh shell      # Django interactive shell
./scripts/setup.sh migrate    # Run database migrations
./scripts/setup.sh stop       # Stop all containers
./scripts/setup.sh clean      # Remove everything (containers, volumes, venv)
```

---

### Option 2: Containerized Development

This mode runs everything in containers, including Django. Use this when you want to test the container build or ensure consistency with CI/CD.

```bash
./scripts/setup.sh dev
```

This starts:
- PostgreSQL/PostGIS container
- Django development server container (with code mounted for hot reload)

Access at http://localhost:8000

---

### 3. Initial Server Setup

Use /scripts/cloud-init.yml and feed it to your VPS provider.


### 4. Create Admin User

```bash
./scripts/setup.sh superuser
```

### 8. Auto-start on Reboot

Containers do not restart automatically after a reboot unless you create a systemd service. Create the unit file:

```bash
cat > /etc/systemd/system/nola-cameras.service << 'EOF'
[Unit]
Description=New Orleans Camera Mapping
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/project-nola-mapping
ExecStart=/usr/bin/podman-compose -f containers/podman-compose.yml --profile prod up -d
ExecStop=/usr/bin/podman-compose -f containers/podman-compose.yml --profile prod down
EnvironmentFile=/opt/project-nola-mapping/.env

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start it:

```bash
systemctl daemon-reload
systemctl enable --now nola-cameras.service
```

Test the reboot path:

```bash
reboot
# After reconnecting:
ssh root@<your-vps-ip>
podman ps   # all three containers should be running
```

### 9. Verify the Deployment

```bash
# All three containers running
podman ps

# TLS and HTTP response
curl -I https://yourdomain.com

# Admin interface reachable
curl -I https://yourdomain.com/admin/
```

### 10. Updating the Application

```bash
cd /opt/project-nola-mapping
git pull
./scripts/setup.sh prod
```

The deploy command rebuilds the web image and restarts containers with zero downtime for the database.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | Generated |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts (comma-separated) | `localhost,127.0.0.1` |
| `DJANGO_DEBUG` | Enable debug mode | `True` |
| `POSTGRES_DB` | Database name | `nola_cameras` |
| `POSTGRES_USER` | Database user | `nola` |
| `POSTGRES_PASSWORD` | Database password | Generated |
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `CSRF_TRUSTED_ORIGINS` | CSRF trusted origins | `http://localhost:8000` |
| `DOMAIN` | Production domain (for Caddy) | `localhost` |

---

## Troubleshooting

### Database connection refused

```bash
# Check if the database container is running
podman ps | grep nola-db

# View database logs
podman logs nola-db

# Restart the database
podman-compose -f containers/podman-compose.yml restart db
```

### GeoDjango import errors

Ensure system dependencies are installed:

```bash
# Fedora
sudo dnf install gdal gdal-devel geos geos-devel proj proj-devel

# Ubuntu
sudo apt install gdal-bin libgdal-dev libgeos-dev libproj-dev
```

### UV not found

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart your terminal
```

### Port 5432 already in use

Another PostgreSQL instance may be running:

```bash
# Check what's using the port
sudo lsof -i :5432

# Stop local PostgreSQL if needed
sudo systemctl stop postgresql
```

### Silverblue: Podman commands not working in toolbox

If `podman` commands fail inside the toolbox:

```bash
# 1. Make sure the host podman socket is running (run on HOST, not in toolbox)
exit  # exit toolbox first
systemctl --user enable --now podman.socket
systemctl --user status podman.socket  # should show "active"

# 2. Re-enter toolbox and verify the socket is accessible
toolbox enter project-nola-mapping
ls -la /run/user/$(id -u)/podman/podman.sock

# 3. Ensure podman-remote is configured
cat ~/.config/containers/containers.conf
# Should contain: remote = true

# 4. Test the connection
podman system connection list
podman ps
```

### Silverblue: Permission denied on podman socket

```bash
# The socket might not be accessible. On the HOST (not toolbox):
podman system connection add --default host unix:///run/user/$(id -u)/podman/podman.sock

# Or reset and recreate:
rm -rf ~/.config/containers/containers.conf
rm -rf ~/.local/share/containers/podman/connections.json

# Then follow the "Configure Podman Access" setup again
```

### Silverblue: Recreating the toolbox

If the toolbox is broken, you can safely delete and recreate it:

```bash
# Exit the toolbox first
exit

# Remove the toolbox
toolbox rm project-nola-mapping

# Recreate it
toolbox create project-nola-mapping
toolbox enter project-nola-mapping

# Reinstall dependencies (your project files in ~ are preserved)
sudo dnf install -y podman-remote gdal gdal-devel geos geos-devel proj proj-devel openssl
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## License

MIT
