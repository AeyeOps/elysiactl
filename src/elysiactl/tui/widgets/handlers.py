"""Simplified handler classes for ConversationView."""

import time
from datetime import datetime
from typing import Any, List, Dict, Optional


class StartupAnimationHandler:
    """Handles the startup animation logic."""

    def __init__(self, widget):
        self.widget = widget
        self.startup_animation_active = False

    def start_startup_animation(self):
        """Start the startup animation."""
        from ...utils.storage import get_user_preference

        # Check if startup animation is enabled
        if not get_user_preference("startup_animation_enabled", True):
            self.widget._show_welcome_message()
            return

        if self.startup_animation_active:
            return

        print("DEBUG Starting Warez-style startup animation")
        self.startup_animation_active = True
        # For now, just complete immediately - can add animation later if needed
        self._complete_startup_animation()

    def _complete_startup_animation(self):
        """Complete the startup animation."""
        print("DEBUG Completing startup animation")
        self.startup_animation_active = False
        self.widget._show_welcome_message()


class BumperEffectHandler:
    """Simplified bumper effect handler."""

    def __init__(self, widget):
        self.widget = widget