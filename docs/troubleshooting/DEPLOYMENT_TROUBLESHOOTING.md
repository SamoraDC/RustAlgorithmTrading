# Deployment Troubleshooting Guide

## Quick Reference

| Error Code | Error Message | Cause | Solution | Priority |
|------------|---------------|-------|----------|----------|
| Exit 1 | `Dependency check failed` | Missing required dependency | Install dependency: `./scripts/install_dependencies.sh` | HIGH |
| Exit 1 | `jq is NOT installed (optional)` | Missing optional dependency | Install: `sudo apt-get install -y jq` or ignore warning | LOW |
| Exit 2 | `Environment not configured` | Missing .env file or vars | Copy `.env.example` to `.env` and configure | HIGH |
| Exit 3 | `Port already in use` | Conflicting service on port | Kill process or change port in config | MEDIUM |
| Exit 4 | `Service failed to start` | Service startup error | Check logs: `./scripts/check_logs.sh` | HIGH |
| Exit 5 | `Database connection error` | Cannot connect to database | Verify database running and credentials | HIGH |
| N/A | `Permission denied` | File permission issue | Fix permissions: `chmod +x scripts/*.sh` | MEDIUM |

## Troubleshooting Flowchart

```
┌─────────────────┐
│  Start Deployment│
└────────┬────────┘
         │
         ▼
┌─────────────────┐     NO    ┌──────────────────────┐
│  Dependencies   ├──────────►│ Install dependencies │
│   Installed?    │            │ ./scripts/install... │
└────────┬────────┘            └───────────┬──────────┘
         │ YES                             │
         │◄────────────────────────────────┘
         ▼
┌─────────────────┐     NO    ┌──────────────────────┐
│  Environment    ├──────────►│ Configure .env file  │
│   Configured?   │            │ Copy .env.example    │
└────────┬────────┘            └───────────┬──────────┘
         │ YES                             │
         │◄────────────────────────────────┘
         ▼
┌─────────────────┐     YES   ┌──────────────────────┐
│  Port Conflict? ├──────────►│ Kill or change port  │
│                 │            │ lsof -ti:PORT | xargs│
└────────┬────────┘            └───────────┬──────────┘
         │ NO                              │
         │◄────────────────────────────────┘
         ▼
┌─────────────────┐     NO    ┌──────────────────────┐
│  Services OK?   ├──────────►│ Check logs & restart │
│                 │            │ Review error details │
└────────┬────────┘            └───────────┬──────────┘
         │ YES                             │
         │◄────────────────────────────────┘
         ▼
┌─────────────────┐
│  SUCCESS! 🎉    │
└─────────────────┘
```

---

## Common Issues and Solutions

### 1. Dependency Check Failures

#### Issue: Optional Dependencies Treated as Required

**Symptom**:
```bash
[✓] docker is installed
[✓] docker-compose is installed
[✓] python3 is installed
[⚠] jq is NOT installed (optional)
[✗] Dependency check failed
```

**Cause**: Script incorrectly treats optional dependencies (jq) as required, causing deployment to fail.

**Solutions**:

**Option A - Install Optional Dependency** (Recommended):
```bash
# Ubuntu/Debian/WSL
sudo apt-get update && sudo apt-get install -y jq

# macOS
brew install jq

# Verify installation
jq --version
```

**Option B - Update Script to Latest Version**:
The fixed version only warns about optional dependencies:
```bash
git pull origin main  # Get latest script updates
./scripts/start_trading.sh
```

**Option C - Manual Workaround**:
If you can't update, edit `scripts/check_dependencies.sh`:
```bash
# Change line that checks jq from:
check_dependency "jq" "optional"

# To ignore exit status:
check_dependency "jq" "optional" || true
```

**Quick Fix Command**:
```bash
./scripts/install_dependencies.sh && ./scripts/start_trading.sh
```

---

#### Issue: Missing Required Dependencies

**Symptom**:
```bash
[✗] docker is NOT installed (required)
[✗] python3 is NOT installed (required)
[✗] Dependency check failed
```

**Solutions**:

**Ubuntu/Debian/WSL**:
```bash
# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Python3
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

**macOS**:
```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install docker docker-compose python3
```

**Automated Installation**:
```bash
./scripts/install_dependencies.sh
```

---

### 2. Port Conflicts

#### Issue: Port Already in Use

**Symptom**:
```bash
Error: bind: address already in use
Cannot start container on port 8080
```

**Identify Process Using Port**:
```bash
# Linux/macOS/WSL
lsof -i :8080
netstat -tulpn | grep 8080

# Windows (PowerShell)
netstat -ano | findstr :8080
```

**Solutions**:

**Option A - Kill Conflicting Process**:
```bash
# Linux/macOS/WSL
lsof -ti:8080 | xargs kill -9

# Windows (PowerShell) - replace PID
taskkill /PID <PID> /F
```

**Option B - Change Port**:
Edit `docker-compose.yml` or `.env`:
```yaml
# docker-compose.yml
ports:
  - "8081:8080"  # Changed from 8080:8080
```

Or in `.env`:
```bash
API_PORT=8081
GRAFANA_PORT=3001
```

**Option C - Stop All Docker Containers**:
```bash
docker-compose down
docker stop $(docker ps -aq)
```

---

### 3. Environment Variable Issues

#### Issue: Missing or Incorrect .env Configuration

**Symptom**:
```bash
Error: EXCHANGE_API_KEY not set
Error: EXCHANGE_SECRET not set
KeyError: 'DATABASE_URL'
```

**Solutions**:

**Step 1 - Check .env Exists**:
```bash
ls -la .env
# If missing:
cp .env.example .env
```

**Step 2 - Verify Required Variables**:
```bash
# Check what's configured
cat .env | grep -v '^#' | grep -v '^$'

# Required variables:
EXCHANGE_API_KEY=your_api_key_here
EXCHANGE_SECRET=your_secret_here
DATABASE_URL=postgresql://user:pass@localhost:5432/trading
REDIS_URL=redis://localhost:6379
```

**Step 3 - Validate Format**:
```bash
# Variables should NOT have spaces around =
# CORRECT:
EXCHANGE_API_KEY=abc123

# WRONG:
EXCHANGE_API_KEY = abc123
```

**Step 4 - Source Environment**:
```bash
# Load into current shell
set -a; source .env; set +a

# Verify
echo $EXCHANGE_API_KEY
```

---

### 4. Database Connection Errors

#### Issue: Cannot Connect to Database

**Symptom**:
```bash
psycopg2.OperationalError: could not connect to server
Connection refused (localhost:5432)
FATAL: password authentication failed
```

**Solutions**:

**Check Database Running**:
```bash
# Docker container
docker ps | grep postgres
docker-compose ps database

# System service
sudo systemctl status postgresql
```

**Start Database**:
```bash
# Docker
docker-compose up -d database

# System service
sudo systemctl start postgresql
```

**Verify Credentials**:
```bash
# Test connection
psql -h localhost -U trading_user -d trading_db

# If password wrong, reset in .env:
DATABASE_URL=postgresql://trading_user:correct_password@localhost:5432/trading_db
```

**Check Port Availability**:
```bash
# Ensure PostgreSQL port is accessible
telnet localhost 5432
nc -zv localhost 5432
```

**Initialize Database**:
```bash
# Run migrations
python3 scripts/init_database.py

# Or use Docker
docker-compose exec database psql -U trading_user -d trading_db -f /docker-entrypoint-initdb.d/init.sql
```

---

### 5. Service Startup Failures

#### Issue: Services Fail to Start

**Symptom**:
```bash
Service 'trading-engine' exited with code 1
Container 'observability' is unhealthy
```

**Solutions**:

**Check Logs**:
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs trading-engine
docker-compose logs -f observability  # Follow mode

# Last 100 lines
docker-compose logs --tail=100
```

**Check Container Status**:
```bash
docker-compose ps
docker ps -a

# Inspect specific container
docker inspect <container_name>
```

**Restart Services**:
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart trading-engine

# Full rebuild
docker-compose down
docker-compose up -d --build
```

**Check Resource Usage**:
```bash
# Docker stats
docker stats

# System resources
free -h
df -h
top
```

**Common Service-Specific Issues**:

**Trading Engine**:
```bash
# Check Rust compilation
cd rust && cargo build --release

# Check config
cat rust/config/trading.toml
```

**Observability Stack**:
```bash
# Check Grafana
curl -f http://localhost:3000/api/health

# Check Prometheus
curl -f http://localhost:9090/-/healthy
```

---

### 6. Permission Errors

#### Issue: Permission Denied on Scripts

**Symptom**:
```bash
bash: ./scripts/start_trading.sh: Permission denied
-rw-r--r-- 1 user user 1234 Dec 1 12:00 start_trading.sh
```

**Solutions**:

**Fix Script Permissions**:
```bash
# Single script
chmod +x scripts/start_trading.sh

# All scripts
chmod +x scripts/*.sh

# Verify
ls -l scripts/*.sh
```

**Fix Docker Socket Permission** (Linux/WSL):
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply changes
newgrp docker

# Or logout/login
```

**Fix File Ownership**:
```bash
# If files owned by root
sudo chown -R $USER:$USER .

# Specific directory
sudo chown -R $USER:$USER scripts/
```

---

### 7. WSL-Specific Issues

#### Issue: Docker Not Accessible in WSL

**Symptom**:
```bash
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solutions**:

**Option A - Enable WSL Integration**:
1. Open Docker Desktop for Windows
2. Settings → Resources → WSL Integration
3. Enable integration for your distro
4. Apply & Restart

**Option B - Start Docker Service**:
```bash
# In WSL
sudo service docker start

# Check status
sudo service docker status
```

**Option C - Fix Docker Socket**:
```bash
# Ensure socket exists and is accessible
ls -l /var/run/docker.sock
sudo chmod 666 /var/run/docker.sock
```

---

#### Issue: Line Ending Issues (CRLF vs LF)

**Symptom**:
```bash
bash: ./script.sh: /bin/bash^M: bad interpreter
```

**Solutions**:

**Fix Line Endings**:
```bash
# Single file
dos2unix scripts/start_trading.sh

# All scripts
find scripts -name "*.sh" -exec dos2unix {} \;

# Or using sed
sed -i 's/\r$//' scripts/*.sh
```

**Configure Git** (Prevent future issues):
```bash
git config --global core.autocrlf input
git config --global core.eol lf

# Re-checkout files
git rm --cached -r .
git reset --hard
```

---

#### Issue: Path Translation Issues

**Symptom**:
```bash
File not found: /mnt/c/Users/...
Windows path not working in WSL
```

**Solutions**:

**Use WSL Paths**:
```bash
# Windows: C:\Users\Name\Project
# WSL:     /mnt/c/Users/Name/Project

# Or move to WSL filesystem for better performance
mkdir -p ~/projects
cp -r /mnt/c/Users/Name/Project ~/projects/
cd ~/projects/Project
```

**Convert Paths**:
```bash
# Windows to WSL
wslpath -u "C:\Users\Name\Project"

# WSL to Windows
wslpath -w "/home/user/project"
```

---

## Platform-Specific Guides

### macOS

**Common Issues**:

1. **Docker Desktop Not Running**:
   ```bash
   open -a Docker
   # Wait for Docker to start
   docker ps
   ```

2. **Homebrew Permissions**:
   ```bash
   sudo chown -R $(whoami) /usr/local/Homebrew
   brew doctor
   ```

3. **Python Version Conflicts**:
   ```bash
   # Use pyenv
   brew install pyenv
   pyenv install 3.11
   pyenv global 3.11
   ```

---

### Ubuntu/Debian

**Common Issues**:

1. **Snap Docker Conflicts**:
   ```bash
   # Remove snap docker
   sudo snap remove docker

   # Install via apt
   sudo apt-get update
   sudo apt-get install docker.io docker-compose
   ```

2. **AppArmor Issues**:
   ```bash
   # Check status
   sudo aa-status

   # Reload profiles
   sudo systemctl reload apparmor
   ```

---

### Docker-Specific

**Common Issues**:

1. **Image Build Failures**:
   ```bash
   # Clean build cache
   docker builder prune -a

   # Rebuild without cache
   docker-compose build --no-cache
   ```

2. **Volume Permission Issues**:
   ```bash
   # In docker-compose.yml
   volumes:
     - ./data:/app/data:z  # SELinux label
   ```

3. **Network Issues**:
   ```bash
   # Recreate network
   docker network prune
   docker-compose down
   docker-compose up -d
   ```

---

## Error Code Reference

### Exit Codes

| Code | Meaning | Common Causes | Debug Command |
|------|---------|---------------|---------------|
| 1 | General Error | Missing dependency, config error | Check logs, verify config |
| 2 | Misuse of Shell | Script syntax error, missing file | Validate script syntax |
| 126 | Cannot Execute | Permission denied, not executable | `chmod +x`, check ownership |
| 127 | Command Not Found | Missing binary, PATH issue | `which <command>`, check PATH |
| 130 | Script Terminated (Ctrl+C) | User interrupted | Restart service |
| 137 | Killed (SIGKILL) | Out of memory, killed by system | Check `dmesg`, monitor resources |
| 143 | Terminated (SIGTERM) | Graceful shutdown | Check why service stopped |

### Service-Specific Codes

**Trading Engine**:
- Exit 10: Configuration error
- Exit 11: Exchange connection failed
- Exit 12: Database initialization failed
- Exit 13: Risk check failed

**Observability**:
- Exit 20: Grafana startup failed
- Exit 21: Prometheus config error
- Exit 22: DuckDB connection failed

---

## Diagnostic Commands

### System Health Check

```bash
#!/bin/bash
# Save as scripts/diagnose.sh

echo "=== System Information ==="
uname -a
cat /etc/os-release

echo -e "\n=== Docker Status ==="
docker --version
docker-compose --version
docker ps -a

echo -e "\n=== Services Status ==="
docker-compose ps

echo -e "\n=== Port Usage ==="
netstat -tulpn | grep -E ':(8080|3000|9090|5432|6379)'

echo -e "\n=== Disk Space ==="
df -h

echo -e "\n=== Memory Usage ==="
free -h

echo -e "\n=== Recent Logs ==="
docker-compose logs --tail=20

echo -e "\n=== Environment Check ==="
[ -f .env ] && echo ".env exists" || echo ".env MISSING"
[ -x scripts/start_trading.sh ] && echo "Scripts executable" || echo "Scripts NOT executable"
```

### Run Diagnostics

```bash
chmod +x scripts/diagnose.sh
./scripts/diagnose.sh > diagnostics.txt 2>&1
```

---

## Quick Fixes

### Complete Reset

```bash
# Stop everything
docker-compose down -v

# Clean Docker
docker system prune -a --volumes -f

# Reset environment
rm -rf data/ logs/
cp .env.example .env

# Rebuild
docker-compose up -d --build
```

### Emergency Restart

```bash
# Kill all processes
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)

# Restart Docker daemon
sudo systemctl restart docker  # Linux
# or restart Docker Desktop

# Start fresh
docker-compose up -d
```

### Fix Permissions (All Scripts)

```bash
find . -name "*.sh" -type f -exec chmod +x {} \;
```

---

## Prevention Best Practices

### Before Deployment

1. **Validate Environment**:
   ```bash
   ./scripts/check_dependencies.sh
   ./scripts/validate_env.sh
   ```

2. **Test Configuration**:
   ```bash
   docker-compose config
   ```

3. **Pre-pull Images**:
   ```bash
   docker-compose pull
   ```

### During Deployment

1. **Monitor Logs**:
   ```bash
   docker-compose logs -f
   ```

2. **Health Checks**:
   ```bash
   ./scripts/health_check.sh
   ```

3. **Resource Monitoring**:
   ```bash
   docker stats
   ```

### After Deployment

1. **Verify Services**:
   ```bash
   curl -f http://localhost:8080/health
   curl -f http://localhost:3000/api/health
   ```

2. **Check Logs for Errors**:
   ```bash
   docker-compose logs | grep -i error
   ```

3. **Backup Configuration**:
   ```bash
   cp .env .env.backup
   ```

---

## Getting Help

### Information to Provide

When seeking help, include:

1. **Error Message**:
   ```bash
   docker-compose logs > logs.txt
   ```

2. **System Info**:
   ```bash
   ./scripts/diagnose.sh > system_info.txt
   ```

3. **Configuration** (sanitized):
   ```bash
   cat docker-compose.yml
   cat .env | sed 's/=.*/=***REDACTED***/'
   ```

4. **Recent Commands**:
   ```bash
   history | tail -20
   ```

### Resources

- **Documentation**: `docs/QUICK_START_OBSERVABILITY.md`
- **GitHub Issues**: Create detailed issue with diagnostics
- **Logs Location**: `logs/` directory
- **Configuration Examples**: `.env.example`, `docker-compose.yml`

---

## Troubleshooting Checklist

```markdown
- [ ] Dependencies installed (`./scripts/check_dependencies.sh`)
- [ ] .env file configured (copy from .env.example)
- [ ] No port conflicts (check with `lsof` or `netstat`)
- [ ] Scripts executable (`chmod +x scripts/*.sh`)
- [ ] Docker daemon running
- [ ] Docker user permissions (added to docker group)
- [ ] Sufficient disk space (>10GB free)
- [ ] Sufficient memory (>4GB available)
- [ ] Database initialized
- [ ] Network connectivity
- [ ] Firewall rules allow connections
- [ ] SELinux/AppArmor not blocking
- [ ] No conflicting services
- [ ] Correct file ownership
- [ ] Line endings correct (LF not CRLF)
```

---

## Success Indicators

Deployment is successful when:

```bash
# All services running
docker-compose ps
# Should show: Up, healthy

# Health checks passing
curl -f http://localhost:8080/health   # Trading API
curl -f http://localhost:3000/api/health  # Grafana
curl -f http://localhost:9090/-/healthy  # Prometheus

# No errors in logs
docker-compose logs | grep -i error
# Should return: no matches

# Databases accessible
psql -h localhost -U trading_user -d trading_db -c "SELECT 1;"
redis-cli ping
```

---

## Appendix: Common Commands Reference

### Docker Commands
```bash
# View logs
docker-compose logs -f [service]

# Restart service
docker-compose restart [service]

# Rebuild service
docker-compose up -d --build [service]

# Stop all
docker-compose down

# Remove volumes
docker-compose down -v

# View resource usage
docker stats

# Shell into container
docker-compose exec [service] bash
```

### Debugging Commands
```bash
# Check service health
docker inspect [container] | jq '.[0].State.Health'

# View environment variables
docker-compose exec [service] env

# Network inspection
docker network ls
docker network inspect [network]

# Volume inspection
docker volume ls
docker volume inspect [volume]
```

### Log Commands
```bash
# Follow logs
docker-compose logs -f

# Specific service
docker-compose logs [service]

# Last N lines
docker-compose logs --tail=100

# Since timestamp
docker-compose logs --since 2024-01-01T00:00:00

# Grep for errors
docker-compose logs | grep -i error
```

---

**Last Updated**: 2025-10-21
**Version**: 1.0.0
**Maintained By**: Hive Mind Swarm - Documenter Agent
