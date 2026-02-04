#!/bin/bash

# ===============================================================
# SBAS- Quick Setup Script
# ===============================================================
# 
# Script for quick setup of ISCE2 + MintPy environment
# Usage: ./setup.sh
#
# ===============================================================

set -euo pipefail

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}ℹ [INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}✅ [SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠ [WARN]${NC} $1"; }
log_error() { echo -e "${RED}❌ [ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}🔄 [STEP]${NC} $1"; }

# Banner
show_banner() {
    echo -e "${CYAN}"
    echo "================================================================"
    echo "    SBAS - Quick Setup"
    echo "    ISCE2 + MintPy Pipeline"
    echo "================================================================"
    echo -e "${NC}"
}

# Check required commands
check_requirements() {
    log_step "Checking required commands..."
    local missing=()
    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi
    if ! docker compose version &> /dev/null; then
        missing+=("docker (with 'docker compose')")
    fi
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing commands:"
        for cmd in "${missing[@]}"; do
            echo "  - $cmd"
        done
        echo
        echo "How to install:"
        echo "  Docker: https://docs.docker.com/get-docker/"
        echo "  Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    log_success "All required commands are available."
}

# Check Docker daemon
check_docker() {
    log_step "Checking Docker daemon..."
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running."
        log_info "Start Docker with:"
        echo "  sudo systemctl start docker  # Linux"
        echo "  Or start Docker Desktop  # Windows/Mac"
        exit 1
    fi
    log_success "Docker is available."
}

# Setup .env file
setup_env_file() {
    log_step "Setting up .env file..."
    # If .env exists, read any existing USERNAME/UID/GID values (do not rely on shell's UID variable)
    local env_username env_uid env_gid
    if [ -f .env ]; then
        env_username=$(grep -m1 '^USERNAME=' .env | sed 's/^USERNAME=//') || env_username=""
        env_uid=$(grep -m1 '^UID=' .env | sed 's/^UID=//') || env_uid=""
        env_gid=$(grep -m1 '^GID=' .env | sed 's/^GID=//') || env_gid=""
    fi
    # Prefer values from .env, otherwise fall back to the current host user
    local username="${env_username:-$(id -un)}"
    local uid="${env_uid:-$(id -u)}"
    local gid="${env_gid:-$(id -g)}"
    if [ ! -f .env ]; then
        log_info "Creating .env file..."
        echo "# ===============================================" > .env
        echo "# Authentication settings" >> .env
        echo "# ===============================================" >> .env
        echo "" >> .env
        echo "# NASA Earthdata credentials" >> .env
        echo "# Required when downloading certain Sentinel-1 products from providers" >> .env
        echo "# that use NASA Earthdata login (e.g., some ASF/ARIA workflows)." >> .env
        echo "# Not required for ALOS downloads." >> .env
        echo "# Register at https://urs.earthdata.nasa.gov/" >> .env
            echo "# (removed Japanese-language note to keep .env template English-only)" >> .env
        echo "EARTHDATA_USER=your_username" >> .env
        echo "EARTHDATA_PASS=your_password" >> .env
        echo "" >> .env
        echo "# Copernicus Dataspace credentials" >> .env
        echo "# Required when downloading data from Copernicus Data Space or services" >> .env
        echo "# that require Copernicus account authentication (some Sentinel-1 sources)." >> .env
        echo "# Optional otherwise; ALOS downloads do not need these." >> .env
        echo "# https://dataspace.copernicus.eu/" >> .env
            echo "# (removed Japanese-language note to keep .env template English-only)" >> .env
        echo "COPERNICUS_USER=your_copernicus_username" >> .env
        echo "COPERNICUS_PASSWORD=your_copernicus_password" >> .env
        echo "" >> .env
        # Project mount defaults
        echo "# Project root on host (default relative path)" >> .env
        echo "PROJECT_ROOT=./workdir" >> .env
        echo "# Optional: external host directory to mount into container (leave empty if not mounting)" >> .env
            echo "# (removed Japanese-language note to keep .env template English-only)" >> .env
        echo "PROJECT_MOUNT=" >> .env
        echo "PROJECT_NAME=" >> .env
        echo "" >> .env
    else
        log_success ".env file already exists."
        if grep -q "your_username" .env; then
            log_warn "Please set authentication info in .env file."
        fi
    fi
    # Add PROJECT_ROOT/PROJECT_MOUNT/PROJECT_NAME if missing
    if ! grep -q "^PROJECT_ROOT=" .env; then
        echo "PROJECT_ROOT=./workdir" >> .env
    fi
    if ! grep -q "^PROJECT_MOUNT=" .env; then
        echo "PROJECT_MOUNT=" >> .env
    fi
    if ! grep -q "^PROJECT_NAME=" .env; then
        echo "PROJECT_NAME=" >> .env
    fi
    # Remove existing USERNAME/UID/GID entries then append
    sed -i '/^USERNAME=/d' .env
    sed -i '/^UID=/d' .env
    sed -i '/^GID=/d' .env
    echo "USERNAME=${username}" >> .env
    echo "UID=${uid}" >> .env
    echo "GID=${gid}" >> .env
    log_success "Set USERNAME, UID, GID in .env"
    log_warn "Please set EARTHDATA_USER/EARTHDATA_PASS and COPERNICUS_USER/COPERNICUS_PASSWORD in your .env file if you will download data that requires them. ALOS downloads do not require these credentials."
    # Prompt for project name and create directory under PROJECT_ROOT
    PROJECT_ROOT_VAL=$(grep -m1 '^PROJECT_ROOT=' .env | sed 's/^PROJECT_ROOT=//')
    PROJECT_ROOT_VAL=${PROJECT_ROOT_VAL:-../workdir}
    # Resolve to absolute path if possible
    if command -v realpath &> /dev/null; then
        project_root_abs=$(realpath -m "${PROJECT_ROOT_VAL}")
    else
        project_root_abs="${PROJECT_ROOT_VAL}"
    fi
    # If PROJECT_NAME already exists in .env, use it; otherwise prompt the user
    proj_name_existing=$(grep -m1 '^PROJECT_NAME=' .env | sed 's/^PROJECT_NAME=//') || proj_name_existing=""
    if [ -n "${proj_name_existing}" ]; then
        pname="${proj_name_existing}"
        log_info "Using existing PROJECT_NAME from .env: ${pname}"
    else
        while true; do
            read -p "Enter project name to create under ${PROJECT_ROOT_VAL} (required): " pname
            if [ -n "${pname}" ]; then
                break
            fi
            echo "Project name cannot be empty."
        done
    fi
    host_project_dir="${project_root_abs%/}/${pname}"
    if mkdir -p "${host_project_dir}" 2>/dev/null; then
        log_success "Created project directory ${host_project_dir}"
    else
        log_warn "Failed to create ${host_project_dir}; please create it manually if needed"
    fi
    # Save PROJECT_NAME to .env
    sed -i '/^PROJECT_NAME=/d' .env
    echo "PROJECT_NAME=${pname}" >> .env

    # Update config.yaml with project_dir
    config_yaml="${PROJECT_ROOT_VAL}/config.yaml"
    if [ -f "${config_yaml}" ]; then
        # Update project_dir in config.yaml to match /work/<project_name>
        sed -i "s|^project_dir:.*|project_dir: /work/${pname}|" "${config_yaml}"
        log_success "Updated ${config_yaml} with project_dir: /work/${pname}"
    else
        log_warn "config.yaml not found at ${config_yaml}; please set project_dir manually"
    fi

    # Ask whether to mount an external host directory into the created project directory
    read -p "Do you want to mount an external host directory into /work/${pname}? (y/N): " mount_resp
    if [[ $mount_resp =~ ^[Yy]$ ]]; then
        while true; do
            read -p "Enter host path to mount (e.g. /mnt/sd_sbas/masters/Jakarta) (leave empty to cancel): " pmount
            if [ -z "${pmount}" ]; then
                log_warn "No host path provided; skipping external mount."
                break
            fi
            if [ ! -d "${pmount}" ]; then
                read -p "Path does not exist. Create it? (y/N): " create_resp
                if [[ $create_resp =~ ^[Yy]$ ]]; then
                    if mkdir -p "${pmount}" 2>/dev/null; then
                        log_info "Created directory ${pmount}"
                    else
                        log_warn "Failed to create ${pmount}; try another path or cancel."
                        continue
                    fi
                else
                    read -p "Enter another path or leave empty to cancel: " alt_pmount
                    pmount="${alt_pmount}"
                    continue
                fi
            fi
            # Save PROJECT_MOUNT to .env
            sed -i '/^PROJECT_MOUNT=/d' .env
            echo "PROJECT_MOUNT=${pmount}" >> .env
            # Generate override to mount external path into /work/<pname>
            cat > docker-compose.override.yml <<EOF
services:
  app:
    volumes:
      - "${pmount}:/work/${pname}"
EOF
            log_success "Created docker-compose.override.yml mapping ${pmount} to /work/${pname}"
            break
        done
    else
        # User chose not to mount external directory: ensure PROJECT_MOUNT is empty
        sed -i '/^PROJECT_MOUNT=/d' .env
        echo "PROJECT_MOUNT=" >> .env
        # Ensure PROJECT_ROOT is set (we mount the project root to /work)
        if ! grep -q "^PROJECT_ROOT=" .env; then
            echo "PROJECT_ROOT=${PROJECT_ROOT_VAL}" >> .env
        fi
        log_info "No external mount selected. Using local project directory under ${PROJECT_ROOT_VAL}."
        log_info "The host path ${PROJECT_ROOT_VAL} will be mounted to /work; project is at /work/${pname}."
    fi
    read -p "Edit .env file now? (y/N): " edit_env
    if [[ $edit_env =~ ^[Yy]$ ]]; then
        if command -v nano &> /dev/null; then
            nano .env
        elif command -v vim &> /dev/null; then
            vim .env
        else
            log_info "Please edit .env file with your preferred editor:"
            echo "  $(pwd)/.env"
        fi
    fi
}
# Prepare Docker environment
prepare_docker_env() {
    log_step "Preparing Docker environment..."
    
    # Check if docker-compose.yml exists
        if [ ! -f ./docker-compose.yml ]; then
        log_error "docker-compose.yml not found"
        exit 1
    fi

    # Ask whether to build the Docker image (first-time build may take a while)
    read -p "Build Docker image now? (Y/n): " build_resp
    if [[ "${build_resp}" =~ ^[Nn]$ ]]; then
        log_warn "Skipping Docker build as requested."
    else
        log_info "Building Docker image... (first build may take a while)"
        docker compose build
    fi

    log_success "Docker environment is ready"
    # Read external mount info from .env and create docker-compose.override.yml if needed
    if [ -f .env ]; then
        # load .env into env without exporting other variables
        set -a
        # shellcheck disable=SC1090
        source .env
        set +a
        if [ -n "${PROJECT_MOUNT:-}" ] && [ -n "${PROJECT_NAME:-}" ]; then
            if [ -d "${PROJECT_MOUNT}" ]; then
                cat > docker-compose.override.yml <<EOF
services:
  app:
    volumes:
      - "${PROJECT_MOUNT}:/work/${PROJECT_NAME}"
EOF
                log_success "Created docker-compose.override.yml (external mount added)"
            else
                log_warn "Specified PROJECT_MOUNT does not exist: ${PROJECT_MOUNT} (override not created)"
            fi
        fi
    fi
}

# Final instructions / usage summary
show_usage() {
    echo
    echo -e "${WHITE}===============================================================${NC}"
    echo -e "${GREEN}🎉 Setup complete!${NC}"
    echo -e "${WHITE}===============================================================${NC}"
    echo
    echo -e "${CYAN}Next steps:${NC}"
    echo
    echo -e "${YELLOW}1. Set credentials (important!)${NC}"
    echo "   Set EARTHDATA_USER and EARTHDATA_PASS in the .env file"
    echo "   NASA Earthdata: https://urs.earthdata.nasa.gov/"
    echo
    echo -e "${YELLOW}2. Start the environment${NC}"
    echo "   Use VS Code Dev Container:"
    echo "     code ."
    echo "     Ctrl+Shift+P > Dev Containers: Reopen in Container"
    echo
    echo "   Or directly with Docker:"
    echo "     cd .devcontainer && docker compose up -d"
    echo "     docker compose exec mintpy-isce2 bash"
    echo
    echo -e "${YELLOW}About project root and external mounts:${NC}"
    echo "  - PROJECT_ROOT in .env controls the host project root mounted to /work (default: ../workdir)."
    echo "  - To mount an external SSD/folder, set PROJECT_MOUNT to the host path and PROJECT_NAME to the project name inside the container."
    echo "    setup.sh will automatically create docker-compose.override.yml when both are set and the host path exists."
    echo "  - If you don't want an external mount, leave PROJECT_MOUNT empty (no override will be created)."
    echo
    echo -e "${YELLOW}3. Configure project${NC}"
    echo "   Edit workdir/config.yaml with your AOI, date range, and processing parameters"
    echo "   project_dir: should match your desired output location (e.g., workdir/jakarta_s1)"
    echo
    echo -e "${YELLOW}4. Run the SBAS pipeline${NC}"
    echo "   cd workdir"
    echo "   python run_pipeline.py --config config.yaml"
    echo
    echo -e "${YELLOW}   Optional parameters:${NC}"
    echo "     --dry-run         : Print commands without executing"
    echo "     --force           : Run steps even if already completed"
    echo "     --only-steps S1 S2: Run only specific steps"
    echo "     --from-step S1    : Start from step S1"
    echo "     --until-step S2   : Stop after step S2"
    echo
    echo -e "${GREEN}See README.md for more details${NC}"
    echo
    echo -e "${WHITE}===============================================================${NC}"
}

main() {
    show_banner

    check_requirements
    check_docker
    setup_env_file
    prepare_docker_env

    show_usage
}

# Execute script
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
