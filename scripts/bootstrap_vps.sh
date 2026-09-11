#!/usr/bin/env bash
# ==============================================================================
# SupplyChainAgent — Fresh Ubuntu 24.04 LTS VPS Bootstrap Script
#
# PURPOSE:
# Prepares a bare Ubuntu 24.04 LTS VPS for production deployment:
# 1. System package updates & base utilities.
# 2. Kernel performance tuning (sysctl & security limits).
# 3. Official Docker Engine & Docker Compose V2 plugin installation.
# 4. SSH-safe UFW firewall configuration (22/custom SSH, 80, 443 TCP/UDP).
# 5. Directory structure setup (/opt/supplychain, /var/backups, /var/log).
#
# SAFETY GUARANTEES:
# - IDEMPOTENT: Safe to run multiple times without duplicating configurations.
# - ZERO CREDENTIALS: Contains no hardcoded passwords, secrets, or tokens.
# - SSH SAFEGUARD: Detects active SSH port before enabling UFW to prevent lockout.
# ==============================================================================

set -euo pipefail

echo "========================================================================"
echo " SupplyChainAgent VPS Host Bootstrap Automation"
echo " Target OS: Ubuntu 24.04 LTS (x86_64 / ARM64)"
echo " Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "========================================================================"

# ------------------------------------------------------------------------------
# 0. Root / Sudo Privilege Check
# ------------------------------------------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
    echo "[-] ERROR: This script must be run as root or via sudo."
    echo "    Usage: sudo bash scripts/bootstrap_vps.sh"
    exit 1
fi

CURRENT_USER="${SUDO_USER:-$(id -un)}"
echo "[+] Running bootstrap as user: ${CURRENT_USER} (Effective UID: 0)"

# ------------------------------------------------------------------------------
# 1. System Package Updates & Essential Tooling
# ------------------------------------------------------------------------------
echo "[+] Step 1/5: Updating system repositories and installing dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    ufw \
    jq \
    git \
    tar \
    gzip \
    procps \
    iptables

# ------------------------------------------------------------------------------
# 2. Host Linux Kernel & Resource Limit Optimization
# ------------------------------------------------------------------------------
echo "[+] Step 2/5: Tuning Linux kernel parameters for Redis & Neo4j..."

# Enable memory overcommit for Redis background saves (BGSAVE / AOF rewrite)
SYSCTL_CONF="/etc/sysctl.d/99-supplychain.conf"
if [ ! -f "${SYSCTL_CONF}" ]; then
    cat << 'EOF' > "${SYSCTL_CONF}"
# SupplyChainAgent Production Kernel Tuning
vm.overcommit_memory = 1
net.core.somaxconn = 1024
EOF
    sysctl -p "${SYSCTL_CONF}" >/dev/null || true
    echo "    -> Applied sysctl tuning: vm.overcommit_memory=1, somaxconn=1024"
else
    echo "    -> Sysctl configuration already present at ${SYSCTL_CONF}."
fi

# Increase maximum open files limits
LIMITS_CONF="/etc/security/limits.d/99-supplychain.conf"
if [ ! -f "${LIMITS_CONF}" ]; then
    cat << 'EOF' > "${LIMITS_CONF}"
* soft nofile 65536
* hard nofile 65536
root soft nofile 65536
root hard nofile 65536
EOF
    echo "    -> Configured file descriptor limits (nofile=65536)."
else
    echo "    -> Resource limits already present at ${LIMITS_CONF}."
fi

# ------------------------------------------------------------------------------
# 3. Official Docker Engine & Docker Compose V2 Installation
# ------------------------------------------------------------------------------
echo "[+] Step 3/5: Installing Docker Engine and Docker Compose V2..."

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "    -> Docker and Compose plugin are already installed."
    docker --version
    docker compose version
else
    # Remove older/conflicting container packages if present
    for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
        apt-get remove -y "${pkg}" >/dev/null 2>&1 || true
    done

    # Setup Docker apt keyring
    install -m 0755 -d /etc/apt/keyrings
    if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
    fi

    # Add official Docker apt repository
    ARCH="$(dpkg --print-architecture)"
    CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME}")"
    cat << EOF > /etc/apt/sources.list.d/docker.list
deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${CODENAME} stable
EOF

    apt-get update -y
    apt-get install -y --no-install-recommends \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin

    systemctl enable --now docker
    echo "    -> Docker Engine successfully installed and enabled."
fi

# Add sudo user to docker group if applicable
if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    usermod -aG docker "${SUDO_USER}" || true
    echo "    -> Added user '${SUDO_USER}' to the 'docker' group."
fi

# ------------------------------------------------------------------------------
# 4. SSH-Safe UFW Firewall Configuration
# ------------------------------------------------------------------------------
echo "[+] Step 4/5: Configuring UFW Host Firewall with SSH Lockout Protection..."

# Detect active SSH port from sshd config, active session, or default 22
DETECTED_SSH_PORT=22
if [ -f /etc/ssh/sshd_config ]; then
    SSHD_PORT_LINE="$(grep -E "^[[:space:]]*Port[[:space:]]+[0-9]+" /etc/ssh/sshd_config | tail -n 1 || true)"
    if [ -n "${SSHD_PORT_LINE}" ]; then
        DETECTED_SSH_PORT="$(echo "${SSHD_PORT_LINE}" | awk '{print $2}')"
    fi
fi
if [ -d /etc/ssh/sshd_config.d ]; then
    SSHD_D_PORT="$(grep -E "^[[:space:]]*Port[[:space:]]+[0-9]+" /etc/ssh/sshd_config.d/*.conf 2>/dev/null | tail -n 1 || true)"
    if [ -n "${SSHD_D_PORT}" ]; then
        DETECTED_SSH_PORT="$(echo "${SSHD_D_PORT}" | awk '{print $2}')"
    fi
fi

echo "    -> Detected SSH Port: ${DETECTED_SSH_PORT}/tcp"

# Set default firewall policies
ufw default deny incoming
ufw default allow outgoing

# CRITICAL SAFETY: Explicitly allow SSH before enabling UFW
ufw allow "${DETECTED_SSH_PORT}/tcp" comment "SSH Remote Management"

# Ingress: Allow HTTP and HTTPS for Caddy
ufw allow 80/tcp comment "HTTP (Caddy Let's Encrypt & Redirect)"
ufw allow 443/tcp comment "HTTPS (Caddy Ingress Reverse Proxy)"
ufw allow 443/udp comment "HTTP/3 QUIC (Caddy High-Performance Ingress)"

# WARNING & ACTIVATION
echo "    -> Enabling UFW firewall (SSH port ${DETECTED_SSH_PORT}, HTTP 80, HTTPS 443 allowed)..."
ufw --force enable
ufw status verbose

# ------------------------------------------------------------------------------
# 5. Directory Structure Setup & Permissions
# ------------------------------------------------------------------------------
echo "[+] Step 5/5: Initializing directory tree for application, backups, and logs..."

APP_DIR="/opt/supplychain"
BACKUP_DIR="/var/backups/supplychain"
LOG_DIR="/var/log/supplychain"

mkdir -p "${APP_DIR}"
mkdir -p "${APP_DIR}/infra/env"
mkdir -p "${BACKUP_DIR}"
mkdir -p "${LOG_DIR}"

# Assign appropriate ownership
if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    chown -R "${SUDO_USER}:${SUDO_USER}" "${APP_DIR}"
    chown -R "${SUDO_USER}:${SUDO_USER}" "${BACKUP_DIR}"
    chown -R "${SUDO_USER}:${SUDO_USER}" "${LOG_DIR}"
fi

# Ensure backup directory permissions are private
chmod 700 "${BACKUP_DIR}"

echo "    -> Application directory: ${APP_DIR}"
echo "    -> Backup directory:      ${BACKUP_DIR} (mode 0700)"
echo "    -> Log directory:         ${LOG_DIR}"

# ------------------------------------------------------------------------------
# Completion & Next Steps
# ------------------------------------------------------------------------------
echo "========================================================================"
echo " VPS Host Bootstrap Completed Successfully"
echo " Docker Version:  $(docker --version)"
echo " Compose Version: $(docker compose version)"
echo " Firewall State:  Active (SSH: ${DETECTED_SSH_PORT}, HTTP: 80, HTTPS: 443)"
echo "========================================================================"
echo ""
echo "NEXT ACTIONS ON VPS:"
echo "1. Clone repository to application directory:"
echo "   git clone https://github.com/HIT-ICES/SupplyChainAgent.git ${APP_DIR}"
echo "   cd ${APP_DIR}"
echo ""
echo "2. Create production environment file:"
echo "   cp infra/env/.env.production.example infra/env/.env.production"
echo "   chmod 600 infra/env/.env.production"
echo ""
echo "3. Generate production secrets (directly on VPS):"
echo "   python3 -c 'import secrets; print(secrets.token_urlsafe(32))'  # for JWT_SECRET"
echo "   python3 -c 'import secrets; print(secrets.token_hex(16))'      # for POSTGRES_PASSWORD"
echo "   python3 -c 'import secrets; print(secrets.token_hex(16))'      # for REDIS_PASSWORD"
echo "   python3 -c 'import secrets; print(secrets.token_hex(16))'      # for NEO4J_PASSWORD"
echo ""
echo "4. Launch backend:"
echo "   - For Domainless Bootstrap (before purchasing a domain):"
echo "     ./scripts/deploy_production.sh --bootstrap"
echo "   - For Full Production (after DNS points api.<DOMAIN> -> <VPS_IP>):"
echo "     ./scripts/deploy_production.sh"
echo "========================================================================"
