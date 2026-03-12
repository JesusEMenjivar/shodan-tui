"""
shodan-tui — entry point

Terminal environment is normalised here, before any Textual/Rich import,
because Rich reads TERM/COLORTERM at import time to decide on color support.
On Wayland compositors (Hyprland, Sway, etc.) these vars are sometimes absent
from the environment, causing raw ANSI escape codes to appear instead of a
rendered TUI.
"""

import os
import sys

# ── Terminal capability guard ─────────────────────────────────────────────────
# Must happen before *any* Textual or Rich import.
_term = os.environ.get("TERM", "")
if not _term or _term == "dumb":
    os.environ["TERM"] = "xterm-256color"

# Inform Rich/Textual that the terminal supports 24-bit colour.
# Most modern terminal emulators (foot, kitty, alacritty, wezterm, ghostty)
# support truecolor; this just makes it explicit when the variable is missing.
if not os.environ.get("COLORTERM"):
    os.environ["COLORTERM"] = "truecolor"
# ─────────────────────────────────────────────────────────────────────────────

from shodan_tui.config import Config, ConfigError


def main() -> None:
    try:
        config = Config.load()
    except ConfigError as e:
        print(f"\n[ERROR] {e}")
        print("\nCreate a .env file with your Shodan API key:")
        print("  SHODAN_API_KEY=your_key_here\n")
        print("Get your API key at: https://account.shodan.io\n")
        sys.exit(1)

    from shodan_tui.app import ShodanTUI
    app = ShodanTUI(config=config)
    app.run()


if __name__ == "__main__":
    main()
