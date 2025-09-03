"""Virtual scrollable widget for mixed content types."""

from datetime import datetime
from typing import Any
import asyncio

from textual import events
from textual.strip import Segment, Strip
from textual.widget import Widget
from textual.color import Color

from ...services.repository import Repository


class VirtualScrollableWidget(Widget):
    """Virtual scrolling widget that can display mixed content types with bumper effects."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content_items: list[dict[str, Any]] = []
        self.start_index = 0  # Which line to start rendering from
        self.visible_count = 20  # How many lines are visible
        self.line_height = 1
        self.selected_item_index = -1
        self.auto_scroll = True  # Auto-scroll to bottom on new content

        # Enhanced scroll features
        self.scroll_velocity = 0  # For smooth scrolling momentum
        self.last_scroll_time = 0  # Timestamp of last scroll
        self.scroll_indicator_visible = False  # Show when not at bottom

        # Bumper effect state
        self.bumper_state = "hidden"  # "hidden", "active", "gray", "fading"
        self.bumper_timer = None
        self.show_top_padding = False
        self.show_bottom_padding = False
        self.last_bumper_activation = 0
        
        # Startup animation state
        self.startup_animation_active = False
        self.startup_animation_lines = []
        self.startup_animation_offset = 0
        self.startup_animation_timer = None
        
        # Make the widget focusable and clickable
        self.can_focus = True

    def _activate_bumper_effect(self, position: str):
        """Activate the bumper effect at top or bottom."""
        import time
        
        current_time = time.time()
        
        # Don't reactivate if already active and within cooldown period
        if (self.bumper_state != "hidden" and 
            current_time - self.last_bumper_activation < 1.0):
            return
            
        self.bumper_state = "active"
        self.last_bumper_activation = current_time
        
        # Cancel any existing timer
        if hasattr(self, 'bumper_timer') and self.bumper_timer:
            try:
                # Try to cancel if it's a timer object
                if hasattr(self.bumper_timer, 'cancel'):
                    self.bumper_timer.cancel()
                elif hasattr(self.bumper_timer, 'stop'):
                    self.bumper_timer.stop()
            except Exception as e:
                print(f"Warning: Could not cancel bumper timer: {e}")
        
        self.bumper_timer = None
        
        # Try to set timer, but handle gracefully if no event loop
        try:
            self.bumper_timer = self.set_timer(2.0, self._bumper_to_gray)
        except RuntimeError:
            # No event loop available, simulate timer manually
            self.bumper_timer = None
            # For testing purposes, just set the state
            pass
        
        # Update padding visibility based on content length
        total_lines = self._get_total_content_lines()
        if total_lines > self.visible_count:
            if position == "top":
                self.show_top_padding = True
                self.show_bottom_padding = False
            else:  # bottom
                self.show_top_padding = False
                self.show_bottom_padding = True
        else:
            # Content fits in viewport, don't show padding
            self.show_top_padding = False
            self.show_bottom_padding = False
            
        self.refresh()

    def _bumper_to_gray(self):
        """Transition bumper to gray color."""
        if self.bumper_state == "active":
            self.bumper_state = "gray"
            try:
                self.bumper_timer = self.set_timer(0.5, self._bumper_fade_out)
            except RuntimeError:
                # No event loop available
                self.bumper_timer = None
            self.refresh()

    def _bumper_fade_out(self):
        """Fade bumper back to background color."""
        if self.bumper_state == "gray":
            self.bumper_state = "fading"
            try:
                self.bumper_timer = self.set_timer(0.5, self._bumper_hide)
            except RuntimeError:
                # No event loop available
                self.bumper_timer = None
            self.refresh()

    def _bumper_hide(self):
        """Hide the bumper completely."""
        self.bumper_state = "hidden"
        self.show_top_padding = False
        self.show_bottom_padding = False
        
        if self.bumper_timer:
            self.bumper_timer.cancel()
            self.bumper_timer = None
            
        self.refresh()

    def scroll_to_bottom(self):
        """Scroll to the bottom of the content (printer style)."""
        total_lines = self._get_total_content_lines()
        if total_lines > self.visible_count:
            self.start_index = total_lines - self.visible_count
        else:
            self.start_index = 0
        self.refresh()

        # Hide scroll indicator when at bottom
        self.scroll_indicator_visible = False

    def scroll_to_bottom_smooth(self, duration: float = 0.3):
        """Smoothly scroll to bottom with animation."""
        import asyncio

        total_lines = self._get_total_content_lines()
        if total_lines <= self.visible_count:
            return

        target_index = total_lines - self.visible_count
        current_index = self.start_index
        distance = target_index - current_index

        if distance == 0:
            return

        # Simple linear animation
        steps = max(5, int(duration * 30))  # 30 FPS
        step_size = distance / steps

        async def animate():
            for i in range(steps):
                self.start_index = int(current_index + step_size * (i + 1))
                self.refresh()
                await asyncio.sleep(duration / steps)

            # Ensure we end exactly at target
            self.start_index = target_index
            self.refresh()

        # Run animation
        asyncio.create_task(animate())

    def is_at_bottom(self) -> bool:
        """Check if we're currently scrolled to the bottom."""
        total_lines = self._get_total_content_lines()
        if total_lines <= self.visible_count:
            return True
        return self.start_index >= total_lines - self.visible_count

    def scroll_up(self, lines: int = 1):
        """Scroll up by the specified number of lines."""
        old_index = self.start_index
        
        # Check if we can actually scroll up
        if old_index <= 0:
            # At top boundary - activate bumper effect
            self._activate_bumper_effect("top")
            return
            
        self.start_index = max(0, self.start_index - lines)

        # Update scroll indicator
        self._update_scroll_indicator()

        # Only refresh if position changed
        if old_index != self.start_index:
            self.auto_scroll = False  # Disable auto-scroll when user manually scrolls
            self.refresh()

    def scroll_down(self, lines: int = 1):
        """Scroll down by the specified number of lines."""
        old_index = self.start_index
        total_lines = self._get_total_content_lines()
        max_start = max(0, total_lines - self.visible_count)
        
        # Check if we can actually scroll down
        if old_index >= max_start:
            # At bottom boundary - activate bumper effect
            self._activate_bumper_effect("bottom")
            return
            
        self.start_index = min(max_start, self.start_index + lines)

        # Update scroll indicator
        self._update_scroll_indicator()

        # Only refresh if position changed
        if old_index != self.start_index:
            self.refresh()

    def _update_scroll_indicator(self):
        """Update the scroll position indicator."""
        self.scroll_indicator_visible = not self.is_at_bottom()
        if not self.scroll_indicator_visible:
            self.auto_scroll = True  # Re-enable auto-scroll when back at bottom

    def _get_total_content_lines(self) -> int:
        """Get the total number of lines in all content items."""
        return sum(len(item.get("lines", [])) for item in self.content_items)

    def on_key(self, event: events.Key):
        """Handle keyboard events for scrolling and startup animation."""
        # Skip startup animation if active
        if self.startup_animation_active:
            print("DEBUG Skipping startup animation due to key press")
            self._complete_startup_animation()
            return
        if event.key == "up":
            self.scroll_up()
            event.prevent_default()
        elif event.key == "down":
            self.scroll_down()
            event.prevent_default()
        elif event.key == "pageup":
            self.scroll_up(self.visible_count // 2)
            event.prevent_default()
        elif event.key == "pagedown":
            self.scroll_down(self.visible_count // 2)
            event.prevent_default()
        elif event.key == "home":
            self.start_index = 0
            self.auto_scroll = False
            self._update_scroll_indicator()
            self.refresh()
            event.prevent_default()
        elif event.key == "end":
            self.scroll_to_bottom()
            self.auto_scroll = True
            self._update_scroll_indicator()
            event.prevent_default()
        elif event.key == "a":  # Toggle auto-scroll
            self.auto_scroll = not self.auto_scroll
            self.notify(f"Auto-scroll {'enabled' if self.auto_scroll else 'disabled'}")
            if self.auto_scroll and self.is_at_bottom():
                self.scroll_to_bottom_smooth()
            event.prevent_default()
        elif event.key == "ctrl+end":  # Force scroll to bottom
            self.scroll_to_bottom_smooth()
            event.prevent_default()

    def on_resize(self, event: events.Resize):
        """Update visible count when widget is resized."""
        old_visible_count = self.visible_count
        self.visible_count = event.size.height
        
        # Hide padding when content fits in viewport
        total_lines = self._get_total_content_lines()
        if total_lines <= self.visible_count:
            self.show_top_padding = False
            self.show_bottom_padding = False
        
        # Re-adjust scroll position if needed
        if self.start_index + self.visible_count > total_lines:
            if self.auto_scroll:
                self.scroll_to_bottom()
            else:
                max_start = max(0, total_lines - self.visible_count)
                self.start_index = min(self.start_index, max_start)
        self.refresh()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp):
        """Handle mouse scroll up with momentum - only if there's content to scroll."""
        # Check if we can actually scroll up
        if self.start_index <= 0:
            # Already at the top, activate bumper effect
            self._activate_bumper_effect("top")
            return

        import time

        current_time = time.time()
        time_delta = current_time - self.last_scroll_time

        # Calculate momentum based on scroll frequency
        if time_delta < 0.1:  # Fast scrolling
            scroll_amount = 5  # Larger scroll for momentum
        else:
            scroll_amount = 3  # Normal scroll

        # Store old position to check if scrolling actually occurred
        old_index = self.start_index

        self.scroll_up(scroll_amount)
        self.last_scroll_time = current_time

        # Only prevent default if we actually scrolled
        if old_index != self.start_index:
            event.prevent_default()

    def on_mouse_scroll_down(self, event: events.MouseScrollDown):
        """Handle mouse scroll down with momentum - only if there's content to scroll."""
        # Check if we can actually scroll down
        total_lines = self._get_total_content_lines()
        max_start = max(0, total_lines - self.visible_count)

        if self.start_index >= max_start:
            # Already at the bottom, activate bumper effect
            self._activate_bumper_effect("bottom")
            return

        import time

        current_time = time.time()
        time_delta = current_time - self.last_scroll_time

        # Calculate momentum based on scroll frequency
        if time_delta < 0.1:  # Fast scrolling
            scroll_amount = 5  # Larger scroll for momentum
        else:
            scroll_amount = 3  # Normal scroll

        # Store old position to check if scrolling actually occurred
        old_index = self.start_index

        self.scroll_down(scroll_amount)
        self.last_scroll_time = current_time

        # Only prevent default if we actually scrolled
        if old_index != self.start_index:
            event.prevent_default()

    def _show_scroll_boundary_feedback(self, boundary: str):
        """Show subtle visual feedback when hitting scroll boundaries."""
        # Update scroll indicator to reflect current state
        self._update_scroll_indicator()

        # Could add visual feedback here in the future:
        # - Subtle animation of the scroll indicator
        # - Brief highlight of boundary area
        # - Haptic feedback (if supported)

        # For now, just ensure the indicator is accurate
        pass
        """Compose the virtual scrolling container."""
        # This widget renders everything via render_line() for performance
        # No child widgets needed
        return []

    def add_text_message(self, text: str, sender: str = "user", timestamp: datetime = None):
        """Add a text message to the scroll."""
        if timestamp is None:
            timestamp = datetime.now()

        # Handle multi-line text by splitting on newlines
        lines = text.split("\n")
        total_lines = len(lines)

        item = {
            "type": "text",
            "content": text,  # Keep original multi-line content
            "lines": lines,  # Store individual lines as list
            "sender": sender,
            "timestamp": timestamp,
            "total_lines": total_lines,
        }
        self.content_items.append(item)
        self.refresh()

        # Enhanced auto-scroll to bottom when new content is added (printer style)
        if self.auto_scroll:
            self.scroll_to_bottom_smooth()

    def add_ai_response(self, response: str, widget_data: dict = None):
        """Add an AI response that may include interactive widgets."""
        lines = response.split("\n")
        total_lines = len(lines)

        item = {
            "type": "ai_response",
            "content": response,
            "lines": lines,  # Store individual lines as list
            "widget_data": widget_data,
            "timestamp": datetime.now(),
            "total_lines": total_lines,
        }
        self.content_items.append(item)
        self.refresh()

        # Enhanced auto-scroll to bottom when new content is added (printer style)
        if self.auto_scroll:
            self.scroll_to_bottom_smooth()

    def add_interactive_table(self, title: str, data: list[dict], actions: list[str] = None):
        """Add an interactive table widget."""
        lines = []
        lines.append(f"📊 {title}")  # Title
        lines.append("─" * 70)  # Separator

        for row in data:
            row_text = " | ".join(f"{k}: {v}" for k, v in row.items())
            lines.append(f"  {row_text}")

        if actions:
            actions_text = " | ".join(f"[{action}]" for action in actions)
            lines.append(f"  Actions: {actions_text}")

        total_lines = len(lines)

        item = {
            "type": "table",
            "title": title,
            "data": data,
            "actions": actions or [],
            "lines": lines,  # Store individual lines as list
            "timestamp": datetime.now(),
            "total_lines": total_lines,
        }
        self.content_items.append(item)
        self.refresh()

        # Enhanced auto-scroll to bottom when new content is added (printer style)
        if self.auto_scroll:
            self.scroll_to_bottom_smooth()

    def add_repository_table(self, repositories: list[Repository]):
        """Add a repository table (similar to current implementation)."""
        # Create table lines
        lines = []
        lines.append("📂 Repositories")  # Header
        lines.append("  Repository       | Status  | Last Sync    | Project")  # Column headers

        for repo in repositories:
            status_emoji = {"success": "✅", "failed": "❌", "syncing": "🔄"}.get(
                repo.sync_status, "❓"
            )

            last_sync = repo.last_sync.strftime("%m-%d %H:%M") if repo.last_sync else "Never"
            repo_name = (
                repo.repository[:15] + "..." if len(repo.repository) > 15 else repo.repository
            )
            project_name = repo.project[:12] + "..." if len(repo.project) > 12 else repo.project

            row = f"  {repo_name:<17} | {status_emoji:<7} | {last_sync:<12} | {project_name}"
            lines.append(row)

        total_lines = len(lines)

        item = {
            "type": "repo_table",
            "repositories": repositories,
            "lines": lines,  # Store individual lines as list
            "timestamp": datetime.now(),
            "total_lines": total_lines,
        }
        self.content_items.append(item)
        self.refresh()

        # Enhanced auto-scroll to bottom when new content is added (printer style)
        if self.auto_scroll:
            self.scroll_to_bottom_smooth()

    def _calculate_text_lines(self, text: str, max_width: int = 80) -> int:
        """Calculate how many lines a text will occupy."""
        words = text.split()
        lines = 1
        current_line_length = 0

        for word in words:
            if current_line_length + len(word) + 1 > max_width:
                lines += 1
                current_line_length = len(word)
            else:
                current_line_length += len(word) + 1

        return lines

    def start_startup_animation(self):
        """Start the Warez/demo scene style startup animation."""
        from ...utils.storage import get_user_preference
        
        # Check if startup animation is enabled
        if not get_user_preference("startup_animation_enabled", True):
            # Skip animation and show welcome directly
            self._show_welcome_message()
            return
            
        if self.startup_animation_active:
            return
            
        print("DEBUG Starting Warez-style startup animation")
        self.startup_animation_active = True
        self.startup_animation_lines = self._generate_startup_animation_lines()
        self.startup_animation_offset = len(self.startup_animation_lines)  # Start with no lines visible
        
        # Start animation loop
        self._animate_startup()

    def _generate_startup_animation_lines(self) -> list[str]:
        """Generate the ASCII art lines for the startup animation."""
        lines = []
        
        # Try to load custom ASCII art file first
        custom_lines = self._load_custom_ascii_art()
        if custom_lines:
            lines.extend(custom_lines)
        else:
            # Use default ASCII art
            lines.extend(self._generate_default_ascii_art())
        
        # Add system information
        lines.extend(self._generate_system_info_lines())
        
        # Add loading animation lines
        lines.extend(self._generate_loading_lines())
        
        # Fill remaining space with animated patterns
        lines.extend(self._generate_filler_lines())
        
        return lines

    def _load_custom_ascii_art(self) -> list[str]:
        """Load custom ASCII art from file if configured."""
        try:
            from ...utils.storage import get_user_preference
            
            custom_file = get_user_preference("startup_animation_file")
            if not custom_file:
                return []
                
            # Resolve path relative to config directory
            import os
            from pathlib import Path
            
            config_dir = Path.home() / ".elysiactl"
            ascii_file = config_dir / custom_file
            
            if ascii_file.exists():
                with open(ascii_file, 'r') as f:
                    return [line.rstrip('\n\r') for line in f.readlines()]
                    
        except Exception as e:
            print(f"Warning: Failed to load custom ASCII art: {e}")
            
        return []

    def _generate_default_ascii_art(self) -> list[str]:
        """Generate the default elysiactl ASCII art."""
        return [
            "",
            "           ▄▄▄█████▓ ██▓ ██▓    ▄▄▄█████▓ ██▓ ▄████▄   ▒█████   ██▓     ██▓    ",
            "           ▓  ██▒ ▓▒▓██▒▓██▒    ▓  ██▒ ▓▒▓██▒▒██▀ ▀█  ▒██▒  ██▒▓██▒   ░██▒   ",
            "           ▒ ▓██░ ▒░▒██▒▒██░    ▒ ▓██░ ▒░▒██▒▒▓█    ▄ ▒██░  ██▒▒██░    ▒██░  ",
            "           ░ ▓██▓ ░ ░██░░██░    ░ ▓██▓ ░ ░██░░▒▓▓▄ ▄██▒▒██   ██░▒██░    ▒██░  ",
            "             ▒██▒ ░ ░██░▓██▒ ░   ▒██▒ ░ ░██░▒ ▓███▀ ░░ ████▓▒░░██████▒░██████▒",
            "             ▒ ░░   ░▓  ▒ ░░     ▒ ░░   ░▓   ░ ░▒ ▒  ░ ▒░▒░▒░ ░ ▒░▓  ░░ ▒░▓  ░",
            "               ░     ▒ ░░ ░        ░     ▒ ░   ░  ▒    ░ ▒ ▒░ ░ ░ ▒  ░░ ░ ▒  ░",
            "             ░       ░  ░ ░      ░ ░     ▒ ░ ░         ░ ░ ░ ▒    ░ ░     ░ ░   ",
            "                       ░              ░       ░ ░         ░ ░      ░  ░    ░  ░ ",
            "",
            "                           [ Repository Management System ]                    ",
            "",
            "                                   by AeyeOps                                 ",
            "",
        ]

    def _generate_system_info_lines(self) -> list[str]:
        """Generate system information lines."""
        import platform
        import datetime
        
        return [
            "",
            f"System: {platform.system()} {platform.release()}",
            f"Python: {platform.python_version()}",
            f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Initializing elysiactl...",
            "",
        ]

    def _generate_loading_lines(self) -> list[str]:
        """Generate loading animation lines."""
        return [
            "[                    ] Loading modules...",
            "[████████████████████] Modules loaded",
            "",
            "[                    ] Connecting to services...",
            "[████████████        ] Connecting to Weaviate...",
            "[████████████████████] Services connected",
            "",
            "Ready for commands!",
            "",
            "Type 'help' for available commands",
            "Press any key to continue...",
        ]

    def _generate_filler_lines(self) -> list[str]:
        """Generate filler lines for remaining space."""
        lines = []
        remaining_lines = self.visible_count - 40  # Approximate lines used by header
        
        if remaining_lines > 0:
            # Add some matrix-style characters
            matrix_chars = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
            
            for i in range(min(remaining_lines, 20)):  # Limit to avoid too much content
                pattern = "".join(matrix_chars[(i * 7 + j) % len(matrix_chars)] for j in range(80))
                lines.append(pattern[:80])  # Limit to 80 chars width
                
        return lines

    def _animate_startup(self):
        """Animate the startup sequence."""
        from ...utils.storage import get_user_preference
        
        if not self.startup_animation_active:
            return
            
        # Move animation up by one line (increase visibility)
        total_lines = len(self.startup_animation_lines)
        if self.startup_animation_offset < total_lines:
            self.startup_animation_offset += 1
            self.refresh()
            
            # Continue animation
            animation_speed = get_user_preference("startup_animation_speed", 0.05)
            try:
                self.startup_animation_timer = self.set_timer(animation_speed, self._animate_startup)
            except RuntimeError:
                # No event loop available
                self.startup_animation_timer = None
                # For demo purposes, just complete animation
                self._complete_startup_animation()
        else:
            # Animation complete
            self._complete_startup_animation()

    def _animate_startup_reverse(self):
        """Animate the startup sequence scrolling down from top."""
        from ...utils.storage import get_user_preference
        
        if not self.startup_animation_active:
            return
            
        # Move animation down by one line (reverse direction)
        total_lines = len(self.startup_animation_lines)
        if self.startup_animation_offset < total_lines:
            self.startup_animation_offset += 1
            self.refresh()
            
            # Continue animation
            animation_speed = get_user_preference("startup_animation_speed", 0.05)
            try:
                self.startup_animation_timer = self.set_timer(animation_speed, self._animate_startup_reverse)
            except RuntimeError:
                # No event loop available
                self.startup_animation_timer = None
                # For demo purposes, just complete animation
                self._complete_startup_animation()
        else:
            # Animation complete
            self._complete_startup_animation()

    def _complete_startup_animation(self):
        """Complete the startup animation and show welcome message."""
        print("DEBUG Completing startup animation")
        self.startup_animation_active = False
        
        # Cancel the animation timer if it exists
        if hasattr(self, 'startup_animation_timer') and self.startup_animation_timer:
            try:
                # Try to cancel if it's a timer object
                if hasattr(self.startup_animation_timer, 'cancel'):
                    self.startup_animation_timer.cancel()
                elif hasattr(self.startup_animation_timer, 'stop'):
                    self.startup_animation_timer.stop()
            except Exception as e:
                print(f"Warning: Could not cancel startup timer: {e}")
        
        self.startup_animation_timer = None
        
        # Clear animation and show welcome message
        self.startup_animation_lines = []
        self.refresh()
        
        # Add the normal welcome message
        self._show_welcome_message()

    def _show_welcome_message(self):
        """Show the welcome messages."""
        self.add_text_message(
            "Welcome to elysiactl! Type 'help' for available commands.", "system"
        )
        self.add_ai_response(
            "Hello! I'm ready to help you manage your repositories. What would you like to do?"
        )

    def _render_startup_animation_line(self, y: int) -> Strip:
        """Render a line from the startup animation (scrolling up from bottom)."""
        if not self.startup_animation_active or not self.startup_animation_lines:
            return Strip([Segment("")])
            
        # For bottom-to-top scrolling:
        # When offset is high (at bottom), show beginning of animation
        # As offset decreases, show later parts, creating upward scroll effect
        total_lines = len(self.startup_animation_lines)
        visible_lines = min(total_lines, self.visible_count)
        
        # Classic scrolling effect: lines scroll up from bottom
        # As offset decreases, lines move up on screen
        animation_line_index = y + (total_lines - self.startup_animation_offset)

        # Only show lines that are within our current reveal window
        if animation_line_index >= total_lines - self.startup_animation_offset and animation_line_index < total_lines:
            line = self.startup_animation_lines[animation_line_index]
            
            # Add some color styling for the animation
            if "elysiactl" in line.lower():
                # Make the title stand out
                return Strip([Segment(line, None, "ai-prefix")])
            elif "[" in line and "]" in line:
                # Progress bars
                return Strip([Segment(line, None, "system-prefix")])
            elif "Ready" in line or "Type" in line:
                # Ready messages
                return Strip([Segment(line, None, "user-prefix")])
            else:
                # Regular animation lines
                return Strip([Segment(line)])
        else:
            return Strip([Segment("")])

    def render_line(self, y: int):
        """Render a specific line for virtual scrolling with startup animation support."""
        if self.startup_animation_active:
            return self._render_startup_animation_line(y)
            
        total_lines = self._get_total_content_lines()
        
        # Check if this is a padding row that should show bumper effect
        # Top padding (4th row from top)
        if y == 3 and self.show_top_padding and total_lines > self.visible_count:
            return self._render_bumper_line()
        
        # Bottom padding (5th row from bottom) 
        if y == self.visible_count - 4 and self.show_bottom_padding and total_lines > self.visible_count:
            return self._render_bumper_line()
        
        # If content fits in viewport, don't show padding
        if total_lines <= self.visible_count:
            self.show_top_padding = False
            self.show_bottom_padding = False
        
        if not self.content_items:
            # Show scroll indicator status in welcome message
            indicator = " 🔽" if self.scroll_indicator_visible else ""
            return Strip([
                Segment("│ ", None, "system-prefix"),
                Segment(f"[{datetime.now().strftime('%H:%M:%S')}] ", None, "message-timestamp"),
                Segment(f"Welcome to elysiactl - type 'help' for commands{indicator}")
            ])

        # Adjust y by start_index for scrolling
        adjusted_y = y + self.start_index

        # Calculate which content item and line within it we're rendering
        current_y = 0

        for item_index, item in enumerate(self.content_items):
            item_lines_count = len(item.get("lines", []))
            item_lines = item.get("lines", [])

            if current_y <= adjusted_y < current_y + item_lines_count:
                # This is the item we need to render
                line_within_item = adjusted_y - current_y
                return self._render_item_line(item, line_within_item, item_index)
            elif adjusted_y < current_y:
                # We've passed the requested line
                break

            current_y += item_lines_count

        # If we get here, we're beyond all content
        # Show scroll indicator if not at bottom
        if self.scroll_indicator_visible:
            return Strip([
                Segment("│ ", None, "ai-prefix"),
                Segment("🔽 Scroll down for more content")
            ])
        else:
            return Strip([Segment("")])

    def _render_bumper_line(self) -> Strip:
        """Render the bumper line with appropriate color."""
        from rich.style import Style
        
        # Get the console width for the bumper line
        try:
            console_width = self.app.console.size.width
        except:
            console_width = 80  # Fallback width
        
        # Create bumper character (horizontal line)
        bumper_char = "─"  # Unicode box-drawing horizontal line
        
        # Determine style based on bumper state
        if self.bumper_state == "active":
            # Initially matches normal text foreground color
            style = Style()  # Use default style
        elif self.bumper_state == "gray":
            # Gray color
            style = Style(color="gray", dim=True)
        elif self.bumper_state == "fading":
            # Fade to background (nearly invisible)
            style = Style(dim=True)
        else:
            # Hidden state - match background
            return Strip([Segment("")])
        
        # Create segments for the bumper line
        # Start at column 2 (index 1) as requested, end at same position on right
        segments = []
        
        # Empty space for first character (column 1)
        segments.append(Segment(" ", style=style))
        
        # Bumper line from column 2 to end (but leave same space on right)
        bumper_length = console_width - 2  # Leave one character space on right
        for i in range(bumper_length):
            segments.append(Segment(bumper_char, style=style))
        
        # Empty space for last character (symmetric)
        segments.append(Segment(" ", style=style))
        
        return Strip(segments)

    def _render_item_line(self, item: dict, line_index: int, item_index: int) -> Strip:
        """Render a specific line within a content item."""
        item_type = item["type"]
        timestamp = item["timestamp"].strftime("%H:%M:%S")

        if item_type == "text":
            return self._render_text_line(item, line_index, timestamp)
        elif item_type == "ai_response":
            return self._render_ai_response_line(item, line_index, timestamp)
        elif item_type == "table":
            return self._render_table_line(item, line_index, timestamp)
        elif item_type == "repo_table":
            return self._render_repo_table_line(item, line_index, timestamp)
        else:
            return Strip([Segment(f"Unknown item type: {item_type}")])

    def _render_text_line(self, item: dict, line_index: int, timestamp: str) -> Strip:
        """Render a line from a text message with sleek vertical line prefix."""
        sender = item["sender"]
        lines = item.get("lines", [])

        # Choose CSS class based on sender (distinct from text foreground)
        if sender == "user":
            # User messages: use accent color
            prefix_class = "user-prefix"
        else:
            # System messages: use warning color
            prefix_class = "system-prefix"

        if line_index == 0:
            # First line with vertical line prefix and timestamp
            first_line = lines[0] if lines else ""
            return Strip([
                Segment("│ ", None, prefix_class),  # Vertical line prefix with CSS class
                Segment(f"[{timestamp}] ", None, "message-timestamp"),  # Timestamp with CSS class
                Segment(first_line)  # Use default text color
            ])
        else:
            # Subsequent lines (continuation of multi-line content)
            # Use same vertical line but without timestamp
            line_offset = line_index - 1
            if line_offset < len(lines):
                line_content = lines[line_offset]
                return Strip([
                    Segment("│ ", None, prefix_class),  # Continued vertical line
                    Segment(f"  {line_content}")  # Indented content
                ])
            else:
                return Strip([Segment("")])

    def _render_ai_response_line(self, item: dict, line_index: int, timestamp: str) -> Strip:
        """Render a line from an AI response with sleek vertical line prefix."""
        lines = item.get("lines", [])

        # AI responses: use success color
        prefix_class = "ai-prefix"

        if line_index == 0:
            # First line with vertical line prefix and timestamp
            first_line = lines[0] if lines else ""
            return Strip([
                Segment("│ ", None, prefix_class),  # Vertical line prefix with CSS class
                Segment(f"[{timestamp}] ", None, "message-timestamp"),  # Timestamp with CSS class
                Segment(first_line)  # Use default text color
            ])
        else:
            # Continuation lines
            line_offset = line_index - 1
            if line_offset < len(lines):
                line_content = lines[line_offset]
                return Strip([
                    Segment("│ ", None, prefix_class),  # Continued vertical line
                    Segment(f"  {line_content}")  # Indented content
                ])
            else:
                return Strip([Segment("")])

    def _render_table_line(self, item: dict, line_index: int, timestamp: str) -> Strip:
        """Render a line from an interactive table."""
        lines = item.get("lines", [])

        if line_index < len(lines):
            return Strip([Segment(lines[line_index])])
        else:
            return Strip([Segment("")])

    def _render_repo_table_line(self, item: dict, line_index: int, timestamp: str) -> Strip:
        """Render a line from a repository table."""
        lines = item.get("lines", [])

        if line_index < len(lines):
            return Strip([Segment(lines[line_index])])
        else:
            return Strip([Segment("")])

    def on_click(self, event: events.Click):
        """Handle clicks for interactive elements."""
        # Add debugging
        self._debug_click(event)

        # Calculate which item was clicked based on mouse position
        # Click coordinates are relative to the widget
        clicked_y = event.y
        current_y = 0

        for item_index, item in enumerate(self.content_items):
            item_lines_count = len(item.get("lines", []))
            item_lines = item.get("lines", [])

            if current_y <= clicked_y < current_y + item_lines_count:
                self._handle_item_click(item, item_index, clicked_y - current_y)
                break

            current_y += item_lines_count

    def _debug_click(self, event: events.Click):
        """Debug click events."""
        # Add some debugging output
        print(f"Click event: x={event.x}, y={event.y}, button={event.button}")
        print(f"Content items count: {len(self.content_items)}")
        for i, item in enumerate(self.content_items):
            lines_info = item.get("lines", [])
            if isinstance(lines_info, list):
                print(f"  Item {i}: type={item.get('type')}, lines_count={len(lines_info)}")
            else:
                print(f"  Item {i}: type={item.get('type')}, lines={lines_info}")

    def _handle_item_click(self, item: dict, item_index: int, line_within_item: int):
        """Handle clicking on a specific item."""
        if item["type"] == "table":
            # Handle table interactions
            data = item["data"]
            actions = item.get("actions", [])

            if line_within_item >= len(data) + 2 and actions:
                # Clicked on actions line
                self.selected_item_index = item_index
                self.post_message(self.TableActionSelected(item_index, actions))
            elif 1 < line_within_item < len(data) + 2:
                # Clicked on data row
                row_index = line_within_item - 2
                self.selected_item_index = item_index
                self.post_message(self.TableRowSelected(item_index, row_index, data[row_index]))


class TableRowSelected(events.Message):
    """Message sent when a table row is selected."""

    def __init__(self, table_index: int, row_index: int, row_data: dict):
        super().__init__()
        self.table_index = table_index
        self.row_index = row_index
        self.row_data = row_data


class TableActionSelected(events.Message):
    """Message sent when a table action is selected."""

    def __init__(self, table_index: int, actions: list[str]):
        super().__init__()
        self.table_index = table_index
        self.actions = actions
