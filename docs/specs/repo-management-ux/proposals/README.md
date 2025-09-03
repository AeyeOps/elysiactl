# **Persistent Interface Layout Proposals - Comparison**
*Evaluating four different approaches for always-accessible commands*

## **Overview**

We've created four distinct proposals for the persistent interface design:

- **Proposal A**: Footer-based design (bottom bar)
- **Proposal B**: Left sidebar design
- **Proposal C**: Right sidebar design
- **Proposal D**: Top bar + footer hybrid

Each proposal includes detailed layouts, pros/cons, and use case recommendations.

## **Quick Comparison Matrix**

| Aspect | Proposal A (Footer) | Proposal B (Left) | Proposal C (Right) | Proposal D (Hybrid) |
|--------|-------------------|------------------|-------------------|-------------------|
| **Space Usage** | Minimal (1 line) | Moderate (20-30 cols) | Moderate (20-30 cols) | Moderate (2 lines) |
| **Content Area** | Maximum width | Reduced width | Reduced width | Maximum width |
| **Navigation** | Simple commands | Rich menu system | Action-focused | Dual navigation |
| **Status Display** | Single line | Multi-section | Multi-section | Multi-line |
| **Terminal Feel** | CLI-native | GUI-like | Modern CLI | Power-user |
| **Best Terminal Width** | Any width | Wide (100+) | Wide (100+) | Any width |
| **Learning Curve** | Low | Medium | Medium | High |

## **Visual Comparison**

### **Proposal A: Footer + Open Prompt Area (Sierra Online Style)**
```
┌─ Main Content Area ──────────────────────────────────────┐
│ [Content scrolls naturally without boundaries]           │
│                                                         │
│ [More content here]                                     │
└───────────────────────────────────────────────────────────┘
💬 What would you like to do with your repositories? ──────┐
│                                                         │
│ > show me repos that failed to sync                     │
│                                                         │
└───────────────────────────────────────────────────────────┘
Command: [add] [status] [logs] [config] [help] [quit] ──┐
Health: ✓ 3 repos | Queue: 0 | Next: 12m                │
```

**Evolution**: Added conversational open prompt area above the footer for natural language interaction, creating Sierra Online-style boundless exploration within defined boundaries.

### **Proposal B: Left Sidebar (Structured Navigation)**
```
┌─ Navigation ──────┬─ Main Content Area ──────────────────┐
│ 📊 Dashboard     │ [Content with reduced width]         │
│ 📋 Repositories  │                                       │
│ 📜 Logs          │ [More content here]                   │
│ ⚙️  Config        │                                       │
│ [A] Add Repo      │                                       │
└───────────────────┴───────────────────────────────────────┘
```

### **Proposal C: Right Sidebar (Action-Focused)**
```
┌─ Main Content Area ──────────────────┬─ Control Panel ──┐
│ [Content with reduced width]         │ 📊 Status        │
│                                     │ [A] Add Repo     │
│ [More content here]                 │ [S] Status       │
│                                     │ [L] Logs         │
└─────────────────────────────────────┴───────────────────┘
```

### **Proposal D: Hybrid (Maximum Information)**
```
┌─ Navigation Bar ── Dashboard ── 3 repos ── ✓ Healthy ────┐
│ [Dashboard] [Repos] [Logs] [Config] [Help] │ Status info │
└───────────────────────────────────────────────────────────┘
┌─ Main Content Area ──────────────────────────────────────┐
│ [Content with full width between header/footer]         │
└───────────────────────────────────────────────────────────┘
Command: [add] [status] [logs] [config] [help] [quit] ──┐
Health: ✓ All Systems | Active: 3 | Queue: 0          │
```

## **Decision Framework**

### **Choose Proposal A (Footer + Open Prompt) if:**
- ✅ You want **Sierra Online-style** open world feeling with natural exploration
- ✅ Users should feel they can **interact boundlessly** within defined boundaries
- ✅ **Conversational experience** is more important than rigid command structure
- ✅ **Progressive discovery** through natural language is the goal
- ✅ Terminal width might be narrow (works with any width)
- ✅ **Agent-like assistance** creates the desired user experience
- ✅ **Exploratory workflows** are common (users asking "what can I do?")

### **Choose Proposal B (Left Sidebar) if:**
- ✅ Users prefer **GUI-like navigation** with clear visual hierarchy
- ✅ You need **detailed status information** with expandability
- ✅ Terminal width is consistently wide (100+ columns)
- ✅ **Structured workflows** with predictable navigation patterns

### **Choose Proposal C (Right Sidebar) if:**
- ✅ **Action-focused** workflows dominate over navigation
- ✅ Content reading is the primary activity (left-side priority)
- ✅ Terminal width is consistently wide (100+ columns)
- ✅ **Quick access to operations** is more important than navigation

### **Choose Proposal D (Hybrid) if:**
- ✅ **Maximum information density** is required from multiple sources
- ✅ Users are **power users** comfortable with complex interfaces
- ✅ Both navigation and actions need to be **always visible**
- ✅ Terminal height is sufficient (25+ lines)
- ✅ **Rich status information** from multiple sources is critical

## **Recommendation**

**For elysiactl's target audience (developers managing repositories):**

🎯 **Proposal A (Footer + Open Prompt)** is now the strongest choice because:
- ✅ **Sierra Online-style experience** creates the boundless feeling you want
- ✅ **Natural language interaction** makes users feel they can explore freely
- ✅ **Conversational agent experience** encourages natural interaction patterns
- ✅ **Simple, clean interface** matches development workflows
- ✅ **Maximum content space** for repository information
- ✅ **Works on any terminal width** (responsive design)
- ✅ **Low learning curve** with high exploration potential

**The open prompt area transforms this from a CLI tool into an interactive experience that feels truly exploratory!** 🚀✨

## **Next Steps**

1. **Review all proposals** in the `proposals/` directory
2. **Choose preferred approach** based on target users and use cases
3. **Create prototype** of the selected design
4. **Test with real users** to validate the choice
5. **Fold selected design** into the main design document

## **Files Created**
- `proposal-a-footer.md` - Footer + Open Prompt Area (Sierra Online-style conversational UX)
- `proposal-b-left-sidebar.md` - Left sidebar navigation
- `proposal-c-right-sidebar.md` - Right sidebar actions
- `proposal-d-top-bar-footer.md` - Top bar + footer hybrid

**Ready to discuss which approach feels right for elysiactl! 🚀**</content>
<parameter name="file_path">/opt/elysiactl/docs/specs/repo-management-ux/proposals/README.md