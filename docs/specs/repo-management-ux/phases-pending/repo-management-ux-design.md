# **ElysiaCtl Repository Management UX - Final Design**
*Consolidated from Proposal A: Footer + Open Prompt Area*

## **🎯 Core Design Decision: Footer + Open Prompt Area**

### **Why This Design?**
After evaluating 4 different persistent interface proposals, we selected **Proposal A** with enhancements:

- ✅ **Footer-based**: Familiar CLI experience (vim/tmux style)
- ✅ **Open prompt area**: Natural language input above footer
- ✅ **Scalable**: Handles dozens to hundreds of repositories
- ✅ **Progressive**: Simple commands → Smart patterns → Agent future
- ✅ **Sierra Online inspiration**: Creates exploratory, boundless feel

### **Final Layout:**
```bash
┌─ Repository Health Dashboard ──────────────────────────────┐
│ 📊 Overall Status: ✓ 147/150 Healthy (98.0% success rate) │
│ 🔄 Active Syncs: 3 (Next batch in 5 min)                  │
│ 📈 Total Documents: 2.3M (45.2 GB)                        │
│ ⚡ Recent Activity: 234 files synced in last hour          │
│                                                           │
│ ┌─ Repository Status ──────────────────────────────────────┤
│ │ Repository          │ Docs │ Last Sync │ Next │ Status  │
│ ├─────────────────────┼──────┼───────────┼──────┼─────────┤
│ │ api-gateway         │ 1247 │ 5m ago   │ 25m │ ✓        │
│ │ user-service        │ 3421 │ 1h ago   │ 29m │ ✓        │
│ │ auth-service        │ 892  │ 3h ago   │ Fail │ ⚠️       │
│ │ [47-52 of 150 repos - ↓ scroll for more]              │
│ └─────────────────────────────────────────────────────────┘
│                                                           │
└─────────────────────────────────────────────────────────────┘
───────────────────────────────────────────────────────────────
💬 What would you like to do with your repositories? ──────────┐
│                                                              │
│ > show me repos that failed to sync                          │
│                                                              │
└───────────────────────────────────────────────────────────────
Command: [add-repo] [status] [logs] [config] [help] [quit] ──┐
Health: ✓ 147/150 repos | Queue: 3 pending | Next: 5m      │
───────────────────────────────────────────────────────────────
```

## **🎨 User Experience Flow**

### **1. Simple Commands (80% of users)**
```bash
elysiactl repo add myorg --watch                  # All repos in org
elysiactl repo add myorg/api-service --watch     # Specific repo
```

### **2. Natural Language (Exploratory)**
```bash
💬 What would you like to do?
> show me repos that failed to sync

# System responds with filtered view
┌─ Filtered: Failing Repositories ────────────────────────┐
│ 🔴 auth-service        │ Docs: 892 │ Last: 3h ago     │
│ 🔴 legacy-api          │ Docs: 445 │ Last: 6h ago     │
│ 🔴 deprecated-svc      │ Docs: 123 │ Last: 12h ago    │
└─────────────────────────────────────────────────────────┘
```

## **⚙️ Technical Architecture**

### **Renderable Views Framework**
```python
# Input → Processing → Renderable View
input = "show me repos that failed to sync"

# Processing pipeline (simple or complex)
if simple_pattern_match(input):
    view = render_simple_filtered_list("failed")
elif agent_needed(input):
    view = agent.process_and_render(input)
else:
    view = render_default_view()

# Result: Always a renderable view
display(view)
```

### **Progressive Implementation Strategy**

#### **Phase 1: Simple Programmatic Views (Current Focus)**
```python
# Direct command mapping
commands = {
    "show failed repos": lambda: render_filtered_list(status="failed"),
    "show python repos": lambda: render_filtered_list(language="python"),
    "repo status": lambda: render_status_table(),
}

# Simple pattern matching
def process_input(input):
    for pattern, renderer in commands.items():
        if pattern in input.lower():
            return renderer()
    return render_default_help()
```

#### **Phase 2: Intelligent Pattern Matching**
```python
# Smart interpretation
intents = {
    r"show.*fail": "render_failed_repos",
    r"show.*python|py": "render_python_repos",
    r"sync.*old|stale": "render_old_repos",
    r"tell.*about": "render_repo_details"
}

def process_input(input):
    for pattern, view_type in intents.items():
        if re.search(pattern, input, re.IGNORECASE):
            return render_view(view_type, extract_params(input))
    return render_help_view()
```

#### **Phase 3: Agent-Driven Views (Future)**
```python
def process_input(input):
    # Try simple patterns first
    simple_result = try_simple_patterns(input)
    if simple_result:
        return simple_result

    # Fall back to agent processing
    agent_response = agent.analyze_and_render(input)

    # Agent returns a renderable view specification
    return render_from_spec(agent_response.view_spec)
```

## **📊 Scalability Features**

### **Progressive Loading Strategy**
```bash
# For dozens of repos (10-50): Show all
┌─ Repository Status ──────────────────────────────────────┤
│ Repository    │ Docs │ Last Sync │ Next Sync │ Status   │
│ myrepo        │ 1247 │ 5m ago   │ 25m      │ ✓ Healthy │
│ user-service  │ 3421 │ 1h ago   │ 29m      │ ✓ Healthy │
│ old-repo      │ 892  │ 3h ago   │ Failed   │ ⚠️ Stale  │
└─────────────────────────────────────────────────────────┘

# For hundreds of repos (50-500): Progressive loading
┌─ Repository Status ──────────────────────────────────────┤
│ Repository          │ Docs │ Last Sync │ Next │ Status  │
│ api-gateway         │ 1247 │ 5m ago   │ 25m │ ✓        │
│ user-service        │ 3421 │ 1h ago   │ 29m │ ✓        │
│ [47-52 of 150 repos - ↓ scroll for more]              │
└─────────────────────────────────────────────────────────┘
```

### **Smart Filtering & Navigation**
```bash
# Natural language filtering
> show me repos that failed to sync
> Found 3 repositories with sync failures...

┌─ Filtered: Failing Repositories ────────────────────────┐
│ 🔴 auth-service        │ Docs: 892 │ Last: 3h ago     │
│ 🔴 legacy-api          │ Docs: 445 │ Last: 6h ago     │
│ 🔴 deprecated-svc      │ Docs: 123 │ Last: 12h ago    │
└─────────────────────────────────────────────────────────┘
```

### **Virtual Scrolling for Performance**
- ✅ Only render visible repositories (20-50 at a time)
- ✅ Load more on scroll with progress indicators
- ✅ Performance optimization for 100+ repositories
### **Virtual Scrolling for Performance**
- ✅ Only render visible repositories (20-50 at a time)
- ✅ Load more on scroll with progress indicators
- ✅ Performance optimization for 100+ repositories
- ✅ Smooth scrolling experience regardless of total count

## **🎯 Command Patterns**

### **Progressive Disclosure (Same as mgit)**
Following mgit's UX philosophy: **simple commands for common cases, advanced options when needed**

#### **Level 1: Simple (80% of users)**
```bash
elysiactl repo add myorg/api-service --watch     # Specific repository
elysiactl repo add myorg --watch                  # All repos in organization
```

#### **Level 2: Intermediate (15% of users)**
```bash
elysiactl repo add myorg --watch --filter api    # Simple pattern matching
elysiactl repo add myorg --watch --first         # Control batch size
elysiactl repo add myorg --watch --dry-run       # Preview operations
```

#### **Level 3: Advanced (5% of users)**
```bash
elysiactl repo add "myorg/backend/*" --watch     # Project-level filtering
elysiactl repo add "*/api-*" --watch             # Cross-org patterns
elysiactl repo add "*" --watch --limit 10        # Full wildcard control
```

### **Batch Control Options**
- ✅ **`--first`**: Add only the first repository matching the pattern
- ✅ **`--limit N`**: Limit to N repositories maximum
- ✅ **`--dry-run`**: Preview what would be added without making changes
- ✅ **`--confirm`**: Require explicit confirmation for batch operations
- ✅ **`--parallel N`**: Control parallelism for large batches

### **Natural Language Examples**
```bash
# Users can type naturally:
> add the api-gateway repository from my org
> show me what's wrong with the failing repo
> sync all repos that haven't updated in 24 hours
> tell me about the codebase structure
> help me troubleshoot the authentication issue
> what repositories are using Python?
```

**Consistent with mgit philosophy - users can be productive immediately with simple commands, then discover advanced features as their needs grow.**---

## 🎯 Grounded in Real MGit JSONL Format

### Actual MGit Output Structure
Based on documented mgit JSONL format from existing elysiactl integration:

```jsonl
// File addition with embedded content (small files)
{"repo": "api-gateway", "op": "add", "path": "src/auth.py", "content": "import flask\n\ndef authenticate():\n    pass", "size": 45, "mime": "text/x-python"}

// File modification with base64 content (binary/medium files)  
{"repo": "frontend", "op": "modify", "path": "assets/logo.png", "content_base64": "iVBORw0KGgoAAAANSUhEUgAA...", "size": 15432, "mime": "image/png"}

// File deletion (minimal info)
{"repo": "legacy-service", "op": "delete", "path": "deprecated.py"}

// File reference for large files
{"repo": "data-pipeline", "op": "modify", "path": "models/large.pkl", "content_ref": "/tmp/mgit/cache/models/large.pkl", "size": 5242880, "mime": "application/octet-stream"}

// Changeset summary (end of repo batch)
{"repo": "api-gateway", "new_changeset": {"commit": "abc123def", "parent": "fed987cba", "branch": "main", "timestamp": "2025-09-02T19:48:52Z"}}
```

### Key Data Fields Available

#### Core Change Information
- ✅ `repo`: Repository identifier
- ✅ `op`: Operation ("add", "modify", "delete")  
- ✅ `path`: File path within repository
- ✅ `size`: File size in bytes
- ✅ `mime`: MIME type for filtering

#### Content Access Patterns
- ✅ `content`: Plain text (small files)
- ✅ `content_base64`: Base64 encoded (binary/medium)
- ✅ `content_ref`: File reference (large files)

#### Repository-Level Metadata
- ✅ `new_changeset`: Commit/branch information
- ✅ `commit`: SHA hash
- ✅ `branch`: Branch name
- ✅ `timestamp`: When change occurred

### TUI Design Grounded in Real Data

#### Repository Overview (Using Real Fields)
```bash
┌─ Repository Status ──────────────────────────────────────┤
│ Repository    │ Files │ Size    │ Last Commit │ Branch   │
├───────────────┼───────┼─────────┼─────────────┼──────────┤
│ api-gateway   │ 1,247 │ 45.2MB │ abc123d     │ main     │
│ frontend      │ 892   │ 156MB  │ fed987c     │ develop  │
│ data-pipeline │ 234   │ 2.3GB  │ xyz789a     │ feature  │
└───────────────┴───────┴─────────┴─────────────┴──────────┘
```

#### File Operation Details (Using Real Fields)
```bash
┌─ Recent Changes ────────────────────────────────────────┐
│ File              │ Operation │ Size    │ MIME Type      │
├───────────────────┼───────────┼─────────┼────────────────┤
│ src/auth.py       │ add       │ 45B     │ text/x-python  │
│ assets/logo.png   │ modify    │ 15.4KB  │ image/png      │
│ deprecated.py     │ delete    │ -       │ -              │
│ models/large.pkl  │ modify    │ 5.2MB   │ application... │
└───────────────────┴───────────┴─────────┴────────────────┘
```

### Smart Content Preview (Using Real Patterns)
```bash
# For text files with 'content' field
> show details src/auth.py
Content: import flask

def authenticate():
    return True

# For binary files with 'content_base64' 
> show details assets/logo.png
Type: PNG Image (15.4KB)
Preview: [Binary content - use 'export' to save]

# For large files with 'content_ref'
> show details models/large.pkl
Type: Pickle file (5.2MB) 
Location: /tmp/mgit/cache/models/large.pkl
Note: Large file - cached locally for processing
```

### Filtering & Search Using Real MIME Types
```bash
# Natural language filtering grounded in real data
> show me python files
# Filters by mime: "text/x-python"

> show image files  
# Filters by mime: "image/*"

> show large files
# Filters by size > threshold

> show recent changes
# Filters by changeset timestamp
```

**By understanding mgit's actual JSONL format, our TUI design is grounded in the real data we'll be working with, ensuring accurate and meaningful displays for users!** 🎯📊

*Format analysis based on actual mgit JSONL output structure documented in existing elysiactl integration specs*

## 🔄 Alternatives Considered

During the design process, we evaluated four different persistent interface approaches before selecting the Footer + Open Prompt Area design:

### Alternative B: Left Sidebar
**Pros:** Clear navigation hierarchy, rich status information, expandable context areas  
**Cons:** Reduces main content width, more complex layout, requires wider terminals  
**Best for:** GUI-like workflows, detailed status needs, users familiar with sidebar navigation

### Alternative C: Right Sidebar  
**Pros:** Action-focused design, content viewing priority, IDE-like familiarity  
**Cons:** Still reduces content area, right-side bias uncommon in terminals  
**Best for:** Frequent action switching, content-focused workflows, wider terminals

### Alternative D: Top Bar + Footer
**Pros:** Maximum information density, dual persistent areas, power-user friendly  
**Cons:** Reduces vertical space, visual complexity, requires taller terminals  
**Best for:** Information-dense workflows, complex navigation needs, sufficient terminal height

### Why We Chose Footer + Open Prompt Area:
- ✅ **Terminal-native**: Familiar to CLI users (vim/tmux style)
- ✅ **Content priority**: Maximum space for repository information
- ✅ **Simple & clean**: Low learning curve, progressive disclosure
- ✅ **Responsive**: Works on any terminal width/height
- ✅ **Sierra Online experience**: Natural language exploration with boundaries

The Footer + Open Prompt Area design strikes the optimal balance between functionality, usability, and the exploratory experience we wanted to create.
