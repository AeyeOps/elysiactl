# Research & Development Workflow Tools
*Knowledge Base - Updated Sept 2025*

## 🔍 Qdrant MCP Semantic Search Patterns

### Collection Structure
- **`textual_rich_typer_context`**: Deep architectural insights, integration patterns, design philosophies
- **`latest_library_features`**: Latest features with practical code examples
- **`qdrant_storage_guide`**: Complete Qdrant storage operations and best practices

### Effective Query Patterns
```python
# Specific library features
query = "textual python library terminal UI"
query = "rich python library terminal formatting"
query = "typer python library CLI commands"

# Integration patterns
query = "textual rich typer integration patterns"
query = "seamless rich textual rendering"

# Performance optimization
query = "virtual scrolling performance optimization"
query = "reactive updates memory management"
```

### Search Strategy
1. **Specific Queries**: Use precise terms for targeted results
2. **Integration Focus**: Query for "seamless" or "integration" patterns
3. **Version Context**: Include version numbers (v0.70+, v13+, v0.12+)
4. **Performance Keywords**: Search for "optimization", "efficient", "virtual"

## 🤖 Perplexity Research Integration

### Query Types
- **Simple**: Fast, cheap (<1M input/output tokens) - basic questions
- **Complex**: Slow, expensive (5M output tokens) - deep analysis, multiple steps

### Effective Research Prompts
```python
# Comprehensive library analysis
query = "Provide comprehensive documentation and examples for Textual, Rich, and Typer Python libraries. Include: 1) Installation and setup, 2) Core concepts and architecture, 3) Key features with code examples, 4) Integration patterns between the libraries, 5) Performance optimization tips, 6) Best practices for modern TUI/CLI development"

# Specific integration patterns
query = "Textual + Rich seamless integration patterns and best practices"

# Performance optimization
query = "Performance optimization strategies for Textual v0.70+ applications"
```

### Research Workflow
1. **Initial Assessment**: Use Qdrant MCP for existing knowledge
2. **Gap Analysis**: Identify missing information
3. **Perplexity Research**: Fill gaps with comprehensive analysis
4. **Knowledge Storage**: Save findings to Qdrant MCP collections
5. **KB Update**: Add to CRUSH.md or KB files for persistence

## 📚 Knowledge Base Internalization Summary

### Textual v0.70+ Core Architecture
- **Reactive Data Model**: `@reactive` properties for automatic UI updates
- **Widget System**: 20+ built-in widgets with composition patterns
- **CSS Styling**: Web-like CSS with terminal-specific properties
- **Virtual Scrolling**: Efficient 100K+ item handling
- **Async Support**: Full asyncio with `@work` decorator

### Rich v13+ Rendering Philosophy
- **Terminal Adaptation**: Progressive enhancement based on capabilities
- **Unicode-First**: Full international character support
- **Performance Conscious**: Efficient rendering for complex layouts
- **Context-Aware**: Automatic adaptation to environment

### Typer v0.12+ CLI Architecture
- **Type-Driven**: Function signatures define CLI interface
- **Rich Integration**: Beautiful output with colors/progress bars
- **Shell Completion**: Auto-generated for bash/zsh/fish/PowerShell
- **Command Groups**: Hierarchical organization with shared state

### Integration Patterns
**Seamless Textual + Rich**:
```python
class RichRenderWidget(Widget):
    def render(self):
        table = Table(title="Data")
        # Rich objects render directly in Textual
        return table
```

**CLI to TUI Bridge**:
```python
@app.command("tui")
def launch_tui():
    """Launch interactive TUI mode"""
    app = RepoManagerApp()
    app.run()
```

### Performance Optimizations
- **Virtual Scrolling**: Only render visible items
- **Background Workers**: `@work` for non-blocking operations
- **Reactive Updates**: Automatic UI updates via data binding
- **Lazy Loading**: On-demand data loading
- **Memory Management**: Efficient resource usage

### Theming Strategy
- **Shared Tokens**: Consistent variables across Textual/Rich
- **Semantic Naming**: Descriptive style names for maintainability
- **Runtime Switching**: Dynamic theme changes
- **Accessibility**: High contrast, readable combinations

## 🚀 Development Workflow Integration

### Smart Learning Strategy
1. **Trial-and-Error Avoidance**: Use Perplexity/Qdrant before manual experimentation
2. **Knowledge Storage**: Save findings to Qdrant MCP with rich metadata
3. **KB Updates**: Add to CRUSH.md for persistence
4. **Workflow Optimization**: Leverage semantic search for "how do I..." questions

### Tool Selection Matrix
| Task | Primary Tool | Secondary | Notes |
|------|-------------|-----------|--------|
| Existing Knowledge | Qdrant MCP | KB files | Fast semantic search |
| New Research | Perplexity | Documentation | Comprehensive analysis |
| Code Examples | KB files | Qdrant MCP | Practical implementations |
| Performance Issues | Perplexity | KB files | Deep optimization analysis |

### Best Practices
- **Qdrant First**: Check existing knowledge before new research
- **Perplexity for Gaps**: Use complex queries for missing information
- **KB Integration**: Store findings for future semantic retrieval
- **Version Awareness**: Include specific version numbers in queries
- **Pattern Recognition**: Search for "integration", "optimization", "best practices"

This workflow knowledge enables efficient development with Textual, Rich, and Typer libraries while maintaining comprehensive documentation and performance optimization.</content>
<file_path>kb/research-development-workflow-tools.md