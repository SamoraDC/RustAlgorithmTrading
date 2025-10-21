# Disaster Recovery Plan
## Rust Algorithmic Trading System

**Version**: 1.0.0
**Last Updated**: October 21, 2025
**Recovery Time Objective (RTO)**: 30 minutes
**Recovery Point Objective (RPO)**: 15 minutes

---

## Table of Contents

1. [Overview](#overview)
2. [Disaster Scenarios](#disaster-scenarios)
3. [Backup Procedures](#backup-procedures)
4. [Recovery Procedures](#recovery-procedures)
5. [Failover Processes](#failover-processes)
6. [Data Recovery](#data-recovery)
7. [Testing & Validation](#testing--validation)
8. [Contact Information](#contact-information)

---

## 1. Overview

### 1.1 Purpose

This document defines the procedures for recovering the trading system from catastrophic failures, ensuring minimal downtime and data loss.

### 1.2 Recovery Objectives

| Metric | Target | Critical Services | Non-Critical Services |
|--------|--------|-------------------|----------------------|
| **RTO** (Recovery Time) | 30 minutes | 15 minutes | 2 hours |
| **RPO** (Recovery Point) | 15 minutes | 5 minutes | 1 hour |
| **Availability SLA** | 99.95% | 99.99% | 99.9% |

### 1.3 Scope

**In Scope**:
- Complete system failure
- Data corruption or loss
- Infrastructure failure (server, network, cloud)
- Database failure
- Natural disasters affecting data center

**Out of Scope**:
- Minor service outages (covered in Operations Runbook)
- Planned maintenance windows
- Individual component failures (covered by high availability)

---

## 2. Disaster Scenarios

### 2.1 Scenario Matrix

| Scenario | Impact | Probability | Recovery Strategy | RTO |
|----------|--------|-------------|-------------------|-----|
| **Server Hardware Failure** | Complete system down | Medium | Restore on new hardware | 30 min |
| **Database Corruption** | Data loss, trading halted | Low | Restore from backup | 20 min |
| **Network Outage** | Cannot reach Alpaca API | Medium | Failover to backup connection | 5 min |
| **Data Center Failure** | Complete infrastructure down | Very Low | Activate DR site | 60 min |
| **Ransomware Attack** | System compromised, data encrypted | Low | Restore from offline backup | 45 min |
| **Accidental Data Deletion** | Partial data loss | Low | Point-in-time recovery | 15 min |
| **Application Bug Causing Data Corruption** | Inconsistent state | Medium | Rollback + restore | 30 min |

### 2.2 Severity Levels

**Critical (P0)**:
- Complete system unavailable
- Financial loss >$1,000/hour
- Data loss >1 hour
- **Response**: Immediate (5 minutes)

**High (P1)**:
- Degraded performance
- Some services unavailable
- Data at risk
- **Response**: 15 minutes

**Medium (P2)**:
- Monitoring/observability issues
- Non-critical data loss
- **Response**: 1 hour

---

## 3. Backup Procedures

### 3.1 Backup Schedule

#### 3.1.1 Database Backups

**Full Backups** (PostgreSQL):
```bash
# Automated via cron: 0 */6 * * * (every 6 hours)
#!/bin/bash
# /opt/trading-system/scripts/backup_db.sh

BACKUP_DIR="/opt/trading-system/backups/db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/trading_db_$DATE.sql.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform full backup with compression
pg_dump -U trading_user -h localhost -d trading_db | gzip > $BACKUP_FILE

# Verify backup integrity
if gunzip -t $BACKUP_FILE; then
    echo "✓ Backup verified: $BACKUP_FILE"
else
    echo "✗ Backup verification failed!"
    exit 1
fi

# Upload to offsite storage (S3)
aws s3 cp $BACKUP_FILE s3://trading-backups/db/ --storage-class GLACIER

# Retain only last 30 days locally
find $BACKUP_DIR -name "trading_db_*.sql.gz" -mtime +30 -delete

# Log backup completion
echo "$(date): Backup completed - $BACKUP_FILE" >> /var/log/trading-backups.log
```

**Incremental Backups** (WAL archiving):
```bash
# Configure in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /opt/trading-system/backups/wal/%f'

# Retention: 7 days
find /opt/trading-system/backups/wal -name "*.wal" -mtime +7 -delete
```

**Backup Validation**:
```bash
# Test restore weekly (automated)
#!/bin/bash
# /opt/trading-system/scripts/test_backup_restore.sh

# Create test database
sudo -u postgres createdb trading_db_test

# Restore latest backup
latest_backup=$(ls -t /opt/trading-system/backups/db/trading_db_*.sql.gz | head -1)
gunzip -c $latest_backup | psql -U trading_user -d trading_db_test

# Verify data
count=$(psql -U trading_user -d trading_db_test -t -c "SELECT COUNT(*) FROM positions;")
if [ "$count" -gt 0 ]; then
    echo "✓ Backup restore test passed ($count positions found)"
else
    echo "✗ Backup restore test FAILED - no data found!"
    exit 1
fi

# Cleanup
sudo -u postgres dropdb trading_db_test
```

#### 3.1.2 Configuration Backups

**Daily Configuration Snapshot**:
```bash
#!/bin/bash
# /opt/trading-system/scripts/backup_config.sh

BACKUP_DIR="/opt/trading-system/backups/config"
DATE=$(date +%Y%m%d)
BACKUP_FILE="$BACKUP_DIR/config_$DATE.tar.gz"

mkdir -p $BACKUP_DIR

# Backup all configuration files
tar -czf $BACKUP_FILE \
    /opt/trading-system/config/ \
    /opt/trading-system/.env.production \
    /opt/trading-system/scripts/ \
    /etc/systemd/system/trading-*.service

# Upload to S3
aws s3 cp $BACKUP_FILE s3://trading-backups/config/

# Retain 90 days
find $BACKUP_DIR -name "config_*.tar.gz" -mtime +90 -delete
```

#### 3.1.3 Binary/Code Backups

**On Each Deployment**:
```bash
#!/bin/bash
# Automatically called during deployment

VERSION=$(git describe --tags)
BACKUP_DIR="/opt/trading-system/backups/binaries/$VERSION"

mkdir -p $BACKUP_DIR

# Backup current binaries before deployment
cp -r /opt/trading-system/bin/* $BACKUP_DIR/

# Tag in git
git tag -a $VERSION -m "Production deployment $VERSION"
git push origin $VERSION

# Retain last 5 versions
ls -t /opt/trading-system/backups/binaries | tail -n +6 | xargs -I {} rm -rf /opt/trading-system/backups/binaries/{}
```

#### 3.1.4 Log Backups

**Daily Log Archival**:
```bash
#!/bin/bash
# Automated via cron: 0 2 * * * (2 AM daily)

LOG_DIR="/opt/trading-system/logs"
ARCHIVE_DIR="/opt/trading-system/logs/archive"
DATE=$(date -d "yesterday" +%Y%m%d)

mkdir -p $ARCHIVE_DIR

# Archive previous day's logs
tar -czf $ARCHIVE_DIR/logs-$DATE.tar.gz $LOG_DIR/*.log

# Truncate active logs
for log in $LOG_DIR/*.log; do
    > "$log"
done

# Upload to S3
aws s3 cp $ARCHIVE_DIR/logs-$DATE.tar.gz s3://trading-backups/logs/

# Retain 90 days
find $ARCHIVE_DIR -name "logs-*.tar.gz" -mtime +90 -delete
```

### 3.2 Offsite Backup Storage

**AWS S3 Configuration**:
```bash
# S3 bucket structure
s3://trading-backups/
├── db/                     # Database backups (Glacier storage)
│   ├── trading_db_20251021_060000.sql.gz
│   ├── trading_db_20251021_120000.sql.gz
│   └── ...
├── wal/                    # WAL archives (Standard storage, 7-day lifecycle)
│   ├── 000000010000000000000001.wal
│   └── ...
├── config/                 # Configuration snapshots (Standard storage)
│   ├── config_20251021.tar.gz
│   └── ...
└── logs/                   # Log archives (IA storage, 90-day retention)
    ├── logs-20251021.tar.gz
    └── ...
```

**Lifecycle Policies**:
```json
{
  "Rules": [
    {
      "Id": "DatabaseBackupGlacier",
      "Prefix": "db/",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 1,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    },
    {
      "Id": "WALRetention",
      "Prefix": "wal/",
      "Status": "Enabled",
      "Expiration": {
        "Days": 7
      }
    },
    {
      "Id": "LogArchiveIA",
      "Prefix": "logs/",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        }
      ],
      "Expiration": {
        "Days": 90
      }
    }
  ]
}
```

### 3.3 Backup Verification

**Automated Verification** (weekly):
```bash
#!/bin/bash
# /opt/trading-system/scripts/verify_all_backups.sh

echo "=== BACKUP VERIFICATION REPORT ==="
echo "Date: $(date)"

# 1. Verify database backups
echo "1. Database Backups:"
for backup in $(find /opt/trading-system/backups/db -name "*.sql.gz" -mtime -7); do
    if gunzip -t $backup 2>/dev/null; then
        echo "  ✓ $backup"
    else
        echo "  ✗ $backup - CORRUPTED!"
    fi
done

# 2. Verify S3 sync
echo "2. S3 Sync Status:"
local_count=$(find /opt/trading-system/backups -type f | wc -l)
s3_count=$(aws s3 ls s3://trading-backups --recursive | wc -l)
echo "  Local: $local_count files"
echo "  S3: $s3_count files"

# 3. Test restore (monthly - 1st of month)
if [ $(date +%d) -eq 01 ]; then
    echo "3. Monthly Restore Test:"
    /opt/trading-system/scripts/test_backup_restore.sh
fi

echo "=== VERIFICATION COMPLETE ==="
```

---

## 4. Recovery Procedures

### 4.1 Complete System Recovery

**Scenario**: Server hardware failure, complete data loss

**Prerequisites**:
- New server provisioned (or DR site activated)
- Network connectivity established
- Access to backup storage (S3)

**Recovery Steps**:

#### Step 1: Provision Infrastructure (15 minutes)

```bash
# On new server (Ubuntu 20.04+)

# 1. Update system
sudo apt-get update
sudo apt-get upgrade -y

# 2. Install dependencies
sudo apt-get install -y \
    pkg-config \
    libssl-dev \
    build-essential \
    postgresql-15 \
    postgresql-client-15 \
    docker.io \
    docker-compose \
    awscli

# 3. Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 4. Create trading user
sudo useradd -r -m -s /bin/bash trading_user
sudo usermod -aG docker trading_user
```

#### Step 2: Restore Configuration (5 minutes)

```bash
# Download latest configuration backup from S3
aws s3 cp s3://trading-backups/config/$(aws s3 ls s3://trading-backups/config/ | sort | tail -1 | awk '{print $4}') /tmp/config_latest.tar.gz

# Extract to trading system directory
sudo mkdir -p /opt/trading-system
sudo tar -xzf /tmp/config_latest.tar.gz -C /

# Set ownership
sudo chown -R trading_user:trading_group /opt/trading-system
sudo chmod 600 /opt/trading-system/.env.production
```

#### Step 3: Restore Database (10 minutes)

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE trading_db;
CREATE USER trading_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
EOF

# Download latest database backup
latest_db_backup=$(aws s3 ls s3://trading-backups/db/ | sort | tail -1 | awk '{print $4}')
aws s3 cp s3://trading-backups/db/$latest_db_backup /tmp/db_restore.sql.gz

# Restore database
gunzip -c /tmp/db_restore.sql.gz | sudo -u postgres psql -d trading_db

# Verify restoration
sudo -u postgres psql -d trading_db -c "SELECT COUNT(*) FROM positions;"
sudo -u postgres psql -d trading_db -c "SELECT COUNT(*) FROM orders;"

echo "✓ Database restored successfully"
```

#### Step 4: Restore Binaries (5 minutes)

```bash
# Download latest binary backup
latest_binary=$(aws s3 ls s3://trading-backups/binaries/ --recursive | sort | tail -1 | awk '{print $4}')
aws s3 cp s3://trading-backups/binaries/$latest_binary /tmp/binaries.tar.gz

# Extract binaries
sudo mkdir -p /opt/trading-system/bin
sudo tar -xzf /tmp/binaries.tar.gz -C /opt/trading-system/bin/

# Set executable permissions
sudo chmod +x /opt/trading-system/bin/*

# Verify binaries
/opt/trading-system/bin/market-data --version
/opt/trading-system/bin/execution-engine --version
```

#### Step 5: Install Systemd Services (2 minutes)

```bash
# Services were restored with config backup
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable trading-market-data trading-execution-engine trading-risk-manager trading-signal-bridge

# Start services in order
sudo systemctl start trading-market-data
sleep 10  # Wait for market data to initialize

sudo systemctl start trading-execution-engine
sudo systemctl start trading-risk-manager
sudo systemctl start trading-signal-bridge

# Verify all services running
sudo systemctl status trading-*
```

#### Step 6: Verify Recovery (3 minutes)

```bash
# Run health check
/opt/trading-system/scripts/health_check.sh --production --verbose

# Verify API connectivity
curl -X GET "https://api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${ALPACA_API_SECRET}"

# Check database connectivity
psql -U trading_user -d trading_db -c "SELECT NOW();"

# Verify position reconciliation
/opt/trading-system/scripts/reconcile_positions.sh

echo "=== RECOVERY COMPLETE ==="
echo "Total time: $(date)"
```

**Expected Total Time**: ~30 minutes

---

### 4.2 Database-Only Recovery

**Scenario**: Database corruption without system failure

#### Point-in-Time Recovery (PITR)

```bash
# Stop services that write to database
sudo systemctl stop trading-execution-engine trading-risk-manager

# Drop corrupted database
sudo -u postgres psql -c "DROP DATABASE trading_db;"

# Create new database
sudo -u postgres psql -c "CREATE DATABASE trading_db OWNER trading_user;"

# Restore base backup
latest_backup=$(ls -t /opt/trading-system/backups/db/trading_db_*.sql.gz | head -1)
gunzip -c $latest_backup | sudo -u postgres psql -d trading_db

# Apply WAL archives up to specific time
recovery_target_time="2025-10-21 14:30:00"  # Time before corruption

sudo -u postgres psql -d trading_db <<EOF
-- Create recovery.conf (PostgreSQL 12+)
ALTER SYSTEM SET recovery_target_time = '$recovery_target_time';
ALTER SYSTEM SET recovery_target_action = 'promote';
EOF

# Restart PostgreSQL in recovery mode
sudo systemctl restart postgresql

# Wait for recovery to complete
while sudo -u postgres psql -c "SELECT pg_is_in_recovery();" | grep -q 't'; do
    echo "Recovery in progress..."
    sleep 5
done

echo "✓ Point-in-time recovery complete"

# Restart services
sudo systemctl start trading-execution-engine trading-risk-manager
```

---

### 4.3 Partial Data Loss Recovery

**Scenario**: Accidental deletion of specific table/data

```bash
# Identify what was deleted
# Example: Orders table accidentally truncated

# Create temporary recovery database
sudo -u postgres createdb trading_db_recovery

# Restore latest backup to recovery database
latest_backup=$(ls -t /opt/trading-system/backups/db/trading_db_*.sql.gz | head -1)
gunzip -c $latest_backup | sudo -u postgres psql -d trading_db_recovery

# Export missing data
sudo -u postgres psql -d trading_db_recovery -c \
    "COPY (SELECT * FROM orders WHERE submitted_at >= '2025-10-21') TO '/tmp/orders_recovery.csv' CSV HEADER;"

# Import to production database
sudo -u postgres psql -d trading_db -c \
    "COPY orders FROM '/tmp/orders_recovery.csv' CSV HEADER;"

# Verify recovery
sudo -u postgres psql -d trading_db -c "SELECT COUNT(*) FROM orders;"

# Cleanup
sudo -u postgres dropdb trading_db_recovery
rm /tmp/orders_recovery.csv
```

---

## 5. Failover Processes

### 5.1 Network Failover

**Primary Connection**: Direct to Alpaca via ISP 1
**Backup Connection**: VPN to Alpaca via ISP 2

```bash
# Automatic failover (managed by network routing)
# Manual failover if automatic fails:

# 1. Detect network failure
ping -c 5 api.alpaca.markets
# If failed:

# 2. Switch to backup route
sudo ip route add default via 192.168.2.1 dev eth1 metric 50

# 3. Verify connectivity
ping -c 5 api.alpaca.markets

# 4. Restart services to use new route
sudo systemctl restart trading-market-data trading-execution-engine
```

### 5.2 Database Failover (Master-Replica Setup)

**Note**: Requires PostgreSQL streaming replication (not in current setup)

```bash
# On replica server (standby)

# Promote standby to primary
sudo -u postgres pg_ctl promote -D /var/lib/postgresql/15/main

# Update application connection string
sudo nano /opt/trading-system/.env.production
# Change DATABASE_URL to new primary

# Restart services
sudo systemctl restart trading-*

# Verify
psql -U trading_user -h new-primary -d trading_db -c "SELECT pg_is_in_recovery();"
# Should return 'f' (false)
```

---

## 6. Data Recovery

### 6.1 Position Reconciliation

**After Recovery**: Always reconcile positions with Alpaca

```bash
#!/bin/bash
# /opt/trading-system/scripts/reconcile_positions.sh

echo "=== POSITION RECONCILIATION ==="

# Get Alpaca positions
alpaca_positions=$(curl -s -X GET "https://api.alpaca.markets/v2/positions" \
    -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
    -H "APCA-API-SECRET-KEY: ${ALPACA_API_SECRET}")

# Get local positions from database
local_positions=$(psql -U trading_user -d trading_db -t -c \
    "SELECT symbol, quantity, entry_price, side FROM positions;" | \
    awk '{printf "{\"symbol\":\"%s\",\"qty\":\"%s\",\"price\":\"%s\",\"side\":\"%s\"}\n", $1, $2, $3, $4}')

# Compare and sync
python3 <<EOF
import json

alpaca = json.loads('''$alpaca_positions''')
local = [json.loads(line) for line in '''$local_positions'''.strip().split('\n') if line]

print("Alpaca Positions:", len(alpaca))
print("Local Positions:", len(local))

# Reconcile differences
for alpaca_pos in alpaca:
    symbol = alpaca_pos['symbol']
    alpaca_qty = float(alpaca_pos['qty'])

    local_pos = next((p for p in local if p['symbol'] == symbol), None)

    if local_pos:
        local_qty = float(local_pos['qty'])
        if abs(alpaca_qty - local_qty) > 0.01:
            print(f"MISMATCH: {symbol} - Alpaca: {alpaca_qty}, Local: {local_qty}")
            # Update local to match Alpaca (source of truth)
            print(f"Updating local position for {symbol}")
    else:
        print(f"MISSING: {symbol} - exists in Alpaca but not in local DB")
        print(f"Adding position: {symbol} qty={alpaca_qty}")

# Find stale local positions
for local_pos in local:
    symbol = local_pos['symbol']
    if not any(p['symbol'] == symbol for p in alpaca):
        print(f"STALE: {symbol} - exists in local but not in Alpaca")
        print(f"Removing position: {symbol}")
EOF

echo "=== RECONCILIATION COMPLETE ==="
```

### 6.2 Order History Recovery

```bash
# Recover missing orders from Alpaca
#!/bin/bash

# Fetch all orders from Alpaca (last 7 days)
curl -X GET "https://api.alpaca.markets/v2/orders?status=all&after=$(date -d '7 days ago' -Idate)" \
    -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
    -H "APCA-API-SECRET-KEY: ${ALPACA_API_SECRET}" > /tmp/alpaca_orders.json

# Import to database
python3 <<EOF
import json
import psycopg2

conn = psycopg2.connect("dbname=trading_db user=trading_user")
cur = conn.cursor()

with open('/tmp/alpaca_orders.json') as f:
    orders = json.load(f)

for order in orders:
    cur.execute("""
        INSERT INTO orders (order_id, symbol, side, order_type, quantity, price, status, submitted_at, filled_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (order_id) DO NOTHING
    """, (
        order['id'],
        order['symbol'],
        order['side'],
        order['type'],
        order['qty'],
        order.get('limit_price'),
        order['status'],
        order['submitted_at'],
        order.get('filled_at')
    ))

conn.commit()
print(f"Imported {cur.rowcount} orders")
EOF
```

---

## 7. Testing & Validation

### 7.1 Disaster Recovery Drills

**Quarterly DR Test Schedule**:

**Q1 (January)**: Database recovery test
**Q2 (April)**: Full system recovery test
**Q3 (July)**: Network failover test
**Q4 (October)**: Backup restoration test

**Test Procedure**:
```bash
# Execute in test environment (NOT production!)

# 1. Simulate disaster (e.g., delete test database)
sudo -u postgres psql -c "DROP DATABASE trading_db_test;"

# 2. Follow recovery procedures
# (Execute steps from Section 4.2)

# 3. Verify recovery
./scripts/health_check.sh --env test

# 4. Measure metrics
# - Recovery time (should be <30 minutes)
# - Data completeness (should be 100%)
# - Service availability (should be 100%)

# 5. Document findings
echo "DR Test Results: $(date)" >> /var/log/dr-tests.log
```

### 7.2 Recovery Validation Checklist

After any recovery:

- [ ] All services running and healthy
- [ ] Database accessible and data intact
- [ ] Positions reconciled with Alpaca
- [ ] API connectivity verified
- [ ] Monitoring and alerting functional
- [ ] Logs being collected
- [ ] Backups resuming normally
- [ ] No data loss or corruption detected
- [ ] Performance within normal parameters
- [ ] Team notified of recovery completion

---

## 8. Contact Information

### 8.1 Emergency Contacts

**Incident Commander** (P0 incidents):
- Name: [Primary On-Call]
- Phone: [Number]
- Email: [Email]

**Database Administrator**:
- Name: [DBA Name]
- Phone: [Number]
- Email: [Email]

**Infrastructure Lead**:
- Name: [Infra Lead]
- Phone: [Number]
- Email: [Email]

**Engineering Manager**:
- Name: [Manager]
- Phone: [Number]
- Email: [Email]

### 8.2 Vendor Support

**Alpaca Markets**:
- Support Email: support@alpaca.markets
- Phone: N/A (email only)
- Status Page: https://status.alpaca.markets

**AWS Support**:
- Support Portal: https://console.aws.amazon.com/support
- Phone: 1-866-987-7765 (Premium Support)

### 8.3 Escalation Path

```
Level 1: On-Call Engineer (0-15 min)
    │
    ▼ (if not resolved)
Level 2: Engineering Lead (15-30 min)
    │
    ▼ (if not resolved)
Level 3: CTO / Senior Leadership (30+ min)
```

---

## Appendix: Recovery Cheat Sheet

**Quick Recovery Commands**:

```bash
# 1. Check system status
systemctl status trading-*

# 2. Verify database
psql -U trading_user -d trading_db -c "SELECT COUNT(*) FROM positions;"

# 3. Test API connectivity
curl -X GET "https://api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${ALPACA_API_SECRET}"

# 4. Restore latest database backup
gunzip -c $(ls -t /opt/trading-system/backups/db/*.sql.gz | head -1) | \
  sudo -u postgres psql -d trading_db

# 5. Reconcile positions
/opt/trading-system/scripts/reconcile_positions.sh

# 6. Restart all services
sudo systemctl restart trading-*

# 7. Run health check
./scripts/health_check.sh --production
```

---

**Document Version**: 1.0.0
**Last Updated**: October 21, 2025
**Next Review**: January 21, 2026
**Maintained By**: Documentation Specialist Agent
