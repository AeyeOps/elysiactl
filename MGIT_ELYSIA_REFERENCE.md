# 🔗 MGIT Index + Elysia Control Integration Guide

## 📋 Quick Reference Card

### 🎯 **Purpose**
This guide shows how to use MGIT index to source repositories and have Elysia Control ingest them automatically, with cron jobs handling differentials and generation.

---

## 🚀 **Quick Setup (3 Steps)**

### **Step 1: Configure MGIT Index**
```bash
# Set up your MGIT index configuration
export MGIT_INDEX_PATH="/path/to/your/mgit/index"
export MGIT_REPOS_LIST="repos-to-index.txt"
export MGIT_UPDATE_INTERVAL="3600"  # 1 hour
```

### **Step 2: Configure Elysia Control**
```bash
# Set Elysia Control environment variables
export ELYSIA_CONTROL_HOST="localhost"
export ELYSIA_CONTROL_PORT="8000"
export ELYSIA_INGEST_BATCH_SIZE="50"
export ELYSIA_DIFF_THRESHOLD="100"  # Min changes to trigger processing
```

### **Step 3: Set Up Cron Job**
```bash
# Add to crontab (crontab -e)
*/30 * * * * /path/to/scripts/mgit-elysia-sync.sh
```

---

## 📁 **Directory Structure**

```
/your/project/
├── scripts/
│   ├── mgit-elysia-sync.sh    # Main sync script
│   ├── mgit-index-update.sh   # Update MGIT index
│   └── elysia-ingest.sh       # Elysia ingestion script
├── config/
│   ├── mgit-config.env        # MGIT configuration
│   └── elysia-config.env      # Elysia Control config
├── logs/
│   ├── mgit-updates.log       # MGIT update logs
│   └── elysia-ingest.log      # Elysia ingestion logs
└── data/
    ├── mgit-index/            # MGIT index data
    └── elysia-processed/      # Processed repo data
```

---

## 🔧 **Configuration Files**

### **mgit-config.env**
```bash
# MGIT Index Configuration
MGIT_INDEX_PATH=/data/mgit-index
MGIT_REPOS_FILE=/config/repos-to-index.txt
MGIT_UPDATE_INTERVAL=3600
MGIT_MAX_REPOS=1000
MGIT_CLONE_DEPTH=1
MGIT_BRANCH=main
```

### **elysia-config.env**
```bash
# Elysia Control Configuration
ELYSIA_HOST=localhost
ELYSIA_PORT=8000
ELYSIA_API_KEY=your-api-key-here
ELYSIA_BATCH_SIZE=50
ELYSIA_TIMEOUT=300
ELYSIA_RETRY_ATTEMPTS=3
```

---

## 📜 **Scripts**

### **mgit-elysia-sync.sh** (Main Sync Script)
```bash
#!/bin/bash
# MGIT Index to Elysia Control Sync Script

set -e

# Load configurations
source /config/mgit-config.env
source /config/elysia-config.env

LOG_FILE="/logs/mgit-elysia-sync.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log "Starting MGIT-Elysia sync process"

# Step 1: Update MGIT index
log "Updating MGIT index..."
/scripts/mgit-index-update.sh

# Step 2: Check for changes
CHANGES=$(find "$MGIT_INDEX_PATH" -name "*.diff" -newer "$MGIT_INDEX_PATH/.last_sync" | wc -l)

if [ "$CHANGES" -gt "$ELYSIA_DIFF_THRESHOLD" ]; then
    log "Found $CHANGES changes, triggering Elysia ingestion..."

    # Step 3: Run Elysia ingestion
    /scripts/elysia-ingest.sh

    # Step 4: Update sync timestamp
    touch "$MGIT_INDEX_PATH/.last_sync"

    log "Sync process completed successfully"
else
    log "Only $CHANGES changes found (threshold: $ELYSIA_DIFF_THRESHOLD), skipping ingestion"
fi
```

### **mgit-index-update.sh**
```bash
#!/bin/bash
# Update MGIT Index Script

source /config/mgit-config.env

log "Updating MGIT index from repos list..."

# Update existing repos
mgit update --index "$MGIT_INDEX_PATH"

# Add new repos from list
while IFS= read -r repo; do
    if [ -n "$repo" ] && [[ $repo != \#* ]]; then
        mgit add "$repo" --index "$MGIT_INDEX_PATH"
    fi
done < "$MGIT_REPOS_FILE"

# Generate differentials
mgit diff --index "$MGIT_INDEX_PATH" --output "$MGIT_INDEX_PATH/diffs/"

log "MGIT index update completed"
```

### **elysia-ingest.sh**
```bash
#!/bin/bash
# Elysia Control Ingestion Script

source /config/elysia-config.env

log "Starting Elysia Control ingestion..."

# Find new/changed repos
find "$MGIT_INDEX_PATH/diffs/" -name "*.json" -type f | while read -r diff_file; do
    log "Processing $diff_file"

    # Extract repo information
    REPO_NAME=$(basename "$diff_file" .json)
    REPO_PATH="$MGIT_INDEX_PATH/repos/$REPO_NAME"

    # Ingest into Elysia Control
    curl -X POST "http://$ELYSIA_HOST:$ELYSIA_PORT/api/ingest/repo" \
         -H "Authorization: Bearer $ELYSIA_API_KEY" \
         -H "Content-Type: application/json" \
         -d @- << EOF
{
    "repo_path": "$REPO_PATH",
    "repo_name": "$REPO_NAME",
    "source": "mgit-index",
    "batch_size": $ELYSIA_BATCH_SIZE,
    "generate_embeddings": true,
    "create_collections": true
}
EOF

    # Check response
    if [ $? -eq 0 ]; then
        log "Successfully ingested $REPO_NAME"
        mv "$diff_file" "$diff_file.processed"
    else
        log "Failed to ingest $REPO_NAME"
    fi
done

log "Elysia Control ingestion completed"
```

---

## ⏰ **Cron Job Setup**

### **Add to Crontab**
```bash
# Edit crontab
crontab -e

# Add this line for 30-minute sync intervals
*/30 * * * * /path/to/scripts/mgit-elysia-sync.sh >> /logs/cron.log 2>&1

# Or for hourly sync
0 * * * * /path/to/scripts/mgit-elysia-sync.sh >> /logs/cron.log 2>&1
```

### **Cron Job Options**
```bash
# Every 30 minutes
*/30 * * * * /scripts/mgit-elysia-sync.sh

# Every hour
0 * * * * /scripts/mgit-elysia-sync.sh

# Every 6 hours
0 */6 * * * /scripts/mgit-elysia-sync.sh

# Daily at 2 AM
0 2 * * * /scripts/mgit-elysia-sync.sh
```

---

## 🔍 **Monitoring & Troubleshooting**

### **Check Sync Status**
```bash
# View recent sync logs
tail -f /logs/mgit-elysia-sync.log

# Check MGIT index status
mgit status --index /data/mgit-index

# Check Elysia Control health
curl http://localhost:8000/health
```

### **Common Issues**

#### **Issue: No changes detected**
```bash
# Check if repos are being updated
ls -la /data/mgit-index/.git/FETCH_HEAD

# Force update
/scripts/mgit-index-update.sh
```

#### **Issue: Elysia ingestion fails**
```bash
# Check Elysia Control logs
tail -f /logs/elysia-control.log

# Test API connection
curl -H "Authorization: Bearer $ELYSIA_API_KEY" http://localhost:8000/api/status
```

#### **Issue: Cron job not running**
```bash
# Check cron status
crontab -l

# Check system logs
grep CRON /var/log/syslog

# Test script manually
/scripts/mgit-elysia-sync.sh
```

---

## 📊 **Performance Tuning**

### **MGIT Index Settings**
```bash
# For faster updates (shallower clones)
MGIT_CLONE_DEPTH=1

# For more comprehensive indexing
MGIT_CLONE_DEPTH=50

# Limit concurrent operations
MGIT_MAX_CONCURRENT=5
```

### **Elysia Control Settings**
```bash
# Larger batches for better throughput
ELYSIA_BATCH_SIZE=100

# Smaller batches for memory efficiency
ELYSIA_BATCH_SIZE=25

# Adjust timeout for large repos
ELYSIA_TIMEOUT=600
```

---

## 🎯 **Quick Commands Reference**

| Command | Purpose |
|---------|---------|
| `mgit update` | Update all indexed repos |
| `mgit add <repo>` | Add new repo to index |
| `mgit diff` | Generate change differentials |
| `curl -X POST /api/ingest/repo` | Ingest repo into Elysia |
| `crontab -e` | Edit cron jobs |
| `tail -f /logs/*.log` | Monitor sync process |

---

## 📞 **Support**

- **Logs**: Check `/logs/` directory for detailed error information
- **Health Checks**: Use provided monitoring scripts
- **Configuration**: Verify all `.env` files are properly set
- **API Docs**: Refer to Elysia Control API documentation

---

**Last Updated**: September 2, 2025
**Version**: 1.0
**Compatibility**: MGIT v2.x, Elysia Control v0.2+