# External Theme Configuration for elysiactl

## Overview
elysiactl now supports externalizing all theme attributes through multiple configuration methods:

1. **JSON Theme Files** - Stored in `~/.elysiactl/themes/`
2. **Environment Variables** - Runtime theme configuration
3. **Built-in Themes** - Default themes that ship with the app

## Theme File Format

Create theme files in `~/.elysiactl/themes/{theme_name}.json`:

```json
{
  "primary": "#00d4ff",
  "secondary": "#8b5cf6",
  "accent": "#ff6b6b",
  "foreground": "#ffffff",
  "background": "#1a1a2e",
  "surface": "#2a2a4e",
  "success": "#00ff88",
  "warning": "#ffa500",
  "error": "#ff4757",
  "panel": "#475569"
}
```

## Environment Variable Configuration

Set themes via environment variables with the pattern `ELYSIACTL_THEME_{THEME_NAME}_{PROPERTY}`:

```bash
export ELYSIACTL_THEME_CORPORATE_PRIMARY="#1e40af"
export ELYSIACTL_THEME_CORPORATE_SECONDARY="#64748b"
export ELYSIACTL_THEME_CORPORATE_BACKGROUND="#0f172a"
# ... etc
```

Then use: `elysiactl --theme corporate`

## Available Theme Properties

- `primary` - Main UI elements, buttons, links
- `secondary` - Secondary UI elements, borders
- `accent` - Highlights, focus states, call-to-action
- `foreground` - Main text color
- `background` - Main background color
- `surface` - Card/panel backgrounds
- `success` - Success states, positive feedback
- `warning` - Warning states, caution messages
- `error` - Error states, negative feedback
- `panel` - Border colors, dividers

## Usage Examples

### Creating a Custom Theme File
```bash
# Create theme directory
mkdir -p ~/.elysiactl/themes

# Create your custom theme
cat > ~/.elysiactl/themes/company.json << EOF
{
  "primary": "#1e40af",
  "secondary": "#64748b", 
  "accent": "#f59e0b",
  "foreground": "#f8fafc",
  "background": "#0f172a",
  "surface": "#1e293b",
  "success": "#10b981",
  "warning": "#f59e0b",
  "error": "#ef4444",
  "panel": "#334155"
}
EOF
```

### Using Environment Variables
```bash
# Set theme colors via environment
export ELYSIACTL_THEME_RUNTIME_PRIMARY="#ff6b6b"
export ELYSIACTL_THEME_RUNTIME_BACKGROUND="#2c3e50"

# Launch with the runtime theme
elysiactl --theme runtime
```

### Built-in Themes
- `default` - Dark theme with cyan/blue accents
- `light` - Light theme with professional colors
- `professional` - Corporate dark theme
- `minimal` - Clean monochrome theme

## Theme Switching
Use the `T` key in the TUI to cycle through available themes, or specify at launch:
```bash
elysiactl --theme company
```

## Theme Development Tips

1. **Test in both light and dark environments**
2. **Ensure sufficient contrast ratios** for accessibility
3. **Use consistent color relationships** (analogous, complementary)
4. **Test with different terminal color schemes**
5. **Consider color blindness** when choosing color combinations

## Troubleshooting

- **Theme not loading**: Check JSON syntax and file permissions
- **Colors not applying**: Ensure property names match exactly
- **Environment variables**: Use all caps with proper prefixes
- **Theme directory**: `~/.elysiactl/themes/` must exist and be writable</content>
<parameter name="file_path">THEME_CONFIGURATION.md