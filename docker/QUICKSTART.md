# Docker Observability - Quick Start Guide

Get the complete observability stack running in 5 minutes.

## ⚡ 3-Step Setup

### 1️⃣ Configure Environment
```bash
cd docker
cp .env.example .env
# Edit .env if needed (optional for testing)
```

### 2️⃣ Start Services
```bash
make up
```

### 3️⃣ Access Dashboards
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📊 Included Services

✅ **Prometheus** - Metrics collection (Port 9090)
✅ **Grafana** - Visualization (Port 3000)
✅ **Alertmanager** - Alert routing (Port 9093)
✅ **Observability API** - Custom metrics (Port 8000)
✅ **Node Exporter** - System metrics (Port 9100)
✅ **cAdvisor** - Container metrics (Port 8080)

## 🎮 Common Commands

```bash
make help          # Show all commands
make up            # Start all services
make down          # Stop all services
make status        # Check service status
make health        # Run health checks
make logs          # View all logs
make logs-api      # View API logs only
make restart       # Restart services
make backup        # Backup all data
```

## 🚀 Integration with Trading System

### Option 1: Use the launcher script
```bash
./docker/start-observability.sh docker
cargo run --release --bin trading_engine
```

### Option 2: Update start_trading.sh
```bash
#!/bin/bash
cd docker && make up && cd ..
sleep 10
cargo run --release --bin trading_engine
```

## 🔍 Verify Setup

```bash
# Check service health
make health

# Expected output:
# ✓ Prometheus: HEALTHY
# ✓ Grafana: HEALTHY
# ✓ Observability API: HEALTHY
```

## 📈 First Steps

1. **View Metrics in Prometheus:**
   - Go to http://localhost:9090
   - Try query: `up` (shows all services)

2. **Create Grafana Dashboard:**
   - Go to http://localhost:3000
   - Login: admin/admin
   - Click "+" → "Dashboard"
   - Add panel with Prometheus query

3. **Check API:**
   - Go to http://localhost:8000/docs
   - Try the `/health` endpoint
   - Explore available metrics endpoints

## 🛑 Stopping Services

```bash
make down          # Stop and keep data
make clean         # Stop and remove all data
```

## 🐛 Troubleshooting

### Services won't start?
```bash
# Check Docker is running
docker info

# Check logs
make logs

# Restart
make restart
```

### Port conflicts?
Edit `docker-compose.observability.yml` and change ports:
```yaml
ports:
  - "19090:9090"  # Changed from 9090
```

### Can't access from host?
On Linux, update Prometheus config:
```yaml
# Use 172.17.0.1 instead of host.docker.internal
- targets: ['172.17.0.1:9091']
```

## 📚 Next Steps

- Read [docker/README.md](./README.md) for detailed docs
- Read [docs/observability/docker-deployment.md](../docs/observability/docker-deployment.md) for advanced config
- Configure custom alerts in `docker/prometheus/alerts.yml`
- Add Grafana dashboards from `docs/grafana/`

## 💡 Pro Tips

1. **Development mode** (hot reload):
   ```bash
   make dev
   ```

2. **View specific logs**:
   ```bash
   make logs-api
   make logs-prometheus
   make logs-grafana
   ```

3. **Shell into containers**:
   ```bash
   make exec-api
   make exec-grafana
   ```

4. **Regular backups**:
   ```bash
   make backup  # Run weekly
   ```

## 🎯 Resource Usage

Typical resource consumption:
- **CPU**: ~0.5-1.0 cores total
- **RAM**: ~1.5-2GB total
- **Disk**: ~1GB for 30 days of metrics

Perfect for paper trading and development!

## 🔒 Security Note

**Default credentials are for DEVELOPMENT ONLY!**

For production:
1. Change Grafana password in `.env`
2. Generate new SECRET_KEY
3. Enable API authentication
4. Use HTTPS reverse proxy

## ✅ Success Checklist

- [ ] Services are running (`make status`)
- [ ] All services healthy (`make health`)
- [ ] Can access Grafana dashboard
- [ ] Can access Prometheus UI
- [ ] Can access API docs
- [ ] Trading system can connect to metrics endpoint

## 🆘 Need Help?

1. Check `make logs` for errors
2. Review [docker/README.md](./README.md)
3. Verify `.env` configuration
4. Ensure no port conflicts
5. Check Docker has enough resources

---

**That's it!** You now have a production-ready observability stack running. 🎉
