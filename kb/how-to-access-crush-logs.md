# How to Access Crush Logs and Conversation History

## Overview
Crush automatically logs all conversations, tool usage, and session data to both a SQLite database and JSON log files. This comprehensive logging system preserves your entire interaction history for review, debugging, and documentation purposes.

## Data Storage Locations

### Primary Database
- **Location**: `{project}/.crush/crush.db`
- **Format**: SQLite database
- **Contents**: All messages, sessions, files, and metadata
- **Size**: Typically 10-50MB per active project

### Log Files
- **Location**: `{project}/.crush/logs/crush.log`
- **Format**: JSON Lines (one JSON object per line)
- **Contents**: Real-time events, tool calls, command executions
- **Access**: Via `crush logs` command

### Configuration Files
- **Global Config**: `~/.config/crush/`
- **Project Config**: `{project}/.crush/`
- **Provider Data**: `~/.local/share/crush/`

## Accessing Logs

### Via Crush CLI
```bash
# View recent logs
crush logs --tail 50

# Follow logs in real-time
crush logs --follow

# View logs from specific project
cd /path/to/project
crush logs --tail 100
```

### Direct Database Access
```bash
# Check message count
sqlite3 .crush/crush.db "SELECT COUNT(*) FROM messages;"

# View recent messages
sqlite3 .crush/crush.db "SELECT role, substr(parts, 1, 100), created_at FROM messages ORDER BY created_at DESC LIMIT 5;"

# View sessions
sqlite3 .crush/crush.db "SELECT id, title, message_count, created_at FROM sessions ORDER BY created_at DESC;"

# View files accessed
sqlite3 .crush/crush.db "SELECT path, content, created_at FROM files ORDER BY created_at DESC LIMIT 10;"
```

### Direct Log File Access
```bash
# View raw JSON logs
tail -20 .crush/logs/crush.log

# Pretty print recent logs
tail -10 .crush/logs/crush.log | jq '.'

# Search for specific events
grep "tool_call" .crush/logs/crush.log | tail -5
```

## Database Schema

### Messages Table
```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,           -- 'user', 'assistant', 'tool'
    parts TEXT NOT NULL,          -- Full message content as JSON
    model TEXT,                   -- AI model used
    created_at INTEGER,           -- Unix timestamp (milliseconds)
    updated_at INTEGER,
    finished_at INTEGER,          -- When response completed
    provider TEXT,                -- AI provider (openai, anthropic, etc.)
    FOREIGN KEY (session_id) REFERENCES sessions (id)
);
```

### Sessions Table
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    parent_session_id TEXT,       -- For threaded conversations
    title TEXT NOT NULL,          -- Auto-generated session title
    message_count INTEGER,        -- Total messages in session
    prompt_tokens INTEGER,        -- Token usage tracking
    completion_tokens INTEGER,
    cost REAL,                    -- Cost tracking
    created_at INTEGER,
    updated_at INTEGER,
    summary_message_id TEXT       -- Reference to summary message
);
```

### Files Table
```sql
CREATE TABLE files (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    path TEXT NOT NULL,           -- File path accessed
    content TEXT NOT NULL,        -- File content (for edits)
    version INTEGER,              -- Version tracking
    created_at INTEGER,
    updated_at INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions (id)
);
```

## Log File Format

Each log entry is a JSON object:
```json
{
  "time": "2025-09-02T19:48:52.975942975-04:00",
  "level": "INFO",
  "source": {
    "function": "github.com/charmbracelet/crush/internal/llm/agent.(*agent).processEvent",
    "file": "/path/to/crush/source/agent.go",
    "line": 686
  },
  "msg": "Tool call started",
  "toolCall": {
    "id": "call_66508865",
    "name": "bash",
    "input": "{\"command\":\"ls -la /opt/elysiactl/.crush/\"}",
    "type": "",
    "finished": false
  }
}
```

## Common Queries

### Find Recent Conversations
```sql
-- Last 10 sessions with message counts
SELECT id, title, message_count, datetime(created_at/1000, 'unixepoch') as created
FROM sessions
ORDER BY created_at DESC
LIMIT 10;
```

### Search Message Content
```sql
-- Find messages containing specific text
SELECT role, substr(parts, 1, 200), datetime(created_at/1000, 'unixepoch')
FROM messages
WHERE parts LIKE '%specific text%'
ORDER BY created_at DESC;
```

### Tool Usage Analysis
```sql
-- Count tool calls by type
SELECT json_extract(parts, '$.data.name') as tool_name, COUNT(*) as count
FROM messages
WHERE role = 'tool' AND json_extract(parts, '$.type') = 'tool_call'
GROUP BY tool_name
ORDER BY count DESC;
```

## Exporting Data

### Export Conversation to JSON
```bash
# Export all messages from a session
sqlite3 .crush/crush.db << 'EOF'
.mode json
SELECT * FROM messages WHERE session_id = 'your-session-id' ORDER BY created_at;
EOF
```

### Export to Markdown
```bash
# Basic conversation export
sqlite3 .crush/crush.db -csv -header "SELECT role, parts, created_at FROM messages WHERE session_id = 'your-session-id' ORDER BY created_at;" > conversation.csv
```

## Privacy and Security

- **Local Storage**: All data stored locally, never transmitted
- **File Permissions**: Database and logs use secure permissions (600)
- **No External Access**: Logs never sent to external services
- **Sensitive Data**: API keys and tokens are masked in logs

## Troubleshooting

### No Logs Found
```bash
# Check if in correct project directory
pwd
ls -la .crush/

# Try specifying data directory
crush logs --data-dir /path/to/project/.crush
```

### Database Locked
```bash
# Close any open Crush sessions
# Wait for WAL files to clear
ls -la .crush/crush.db*

# Force unlock if needed
sqlite3 .crush/crush.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

### Large Log Files
```bash
# Compress old logs
gzip .crush/logs/crush.log.1

# Rotate logs manually
mv .crush/logs/crush.log .crush/logs/crush.log.$(date +%Y%m%d_%H%M%S)
```

## Performance Notes

- **Database Size**: Expect 10-50MB per active project
- **Log Rotation**: Logs are not automatically rotated
- **Query Performance**: Add indexes for frequent queries
- **Backup**: Consider periodic database backups for long-term projects

## Integration with Development Workflow

- **Debugging**: Use logs to troubleshoot tool issues
- **Progress Tracking**: Monitor message counts for project progress
- **Cost Analysis**: Track token usage and costs over time
- **Documentation**: Export conversations for project documentation
- **Knowledge Base**: Build searchable knowledge from conversation history

---

**This logging system ensures that every interaction, decision, and creative insight is preserved for future reference and analysis.**</content>
<parameter name="file_path">/opt/elysiactl/kb/how-to-access-crush-logs.md