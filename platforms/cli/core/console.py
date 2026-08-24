"""
Console management for consistent CLI output.
"""

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.tree import Tree
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.align import Align
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    class Panel:
        def __init__(self, renderable, *args, **kwargs):
            self.renderable = renderable
    class Text:
        def __init__(self, text=""):
            self.text = text
        def append(self, text, *args, **kwargs):
            self.text += text
    class Console:
        def __init__(self, *args, **kwargs):
            pass
        def print(self, *args, **kwargs):
            import re
            cleaned_args = []
            for arg in args:
                if isinstance(arg, Panel):
                    cleaned_args.append(str(getattr(arg.renderable, 'text', str(arg.renderable))))
                elif isinstance(arg, Text):
                    cleaned_args.append(arg.text)
                elif isinstance(arg, str):
                    cleaned_args.append(re.sub(r"\[/?\w+.*?\]", "", arg))
                else:
                    cleaned_args.append(str(arg))
            print(*cleaned_args)

from typing import Optional
import sys

from .theme import Theme

# Global console instance
_console = None

def get_console():
    """Get the global console instance."""
    global _console
    if _console is None:
        _console = Console()
    return _console

def print_banner(compact: bool = False):
    """Print the TinyTorch banner using Rich with clean block text style."""
    console = get_console()
    if compact:
        print_compact_banner()
    else:
        # Create banner text that matches the clean block text theme
        banner_text = Text()
        banner_text.append("Tiny", style=Theme.BRAND_ACCENT)
        banner_text.append("🔥", style=Theme.BRAND_FLAME)
        banner_text.append("TORCH", style=Theme.BRAND_PRIMARY)
        banner_text.append(": Don't import it. Build it.", style=Theme.DIM)
        console.print(Panel(banner_text, style=Theme.BORDER_DEFAULT, padding=(1, 2)))

def print_compact_banner():
    """Print a compact TinyTorch banner with 'Tiny' above TORCH."""
    console = get_console()
    # Create compact banner text
    banner_text = Text()
    banner_text.append("Tiny", style=Theme.BRAND_ACCENT)
    banner_text.append("\n🔥", style=Theme.BRAND_FLAME)
    banner_text.append("TORCH", style=Theme.BRAND_PRIMARY)
    banner_text.append(": Don't import it. Build it.", style=Theme.DIM)
    console.print(Panel(banner_text, style=Theme.BORDER_DEFAULT, padding=(1, 2)))

def print_ascii_logo(compact: bool = False):
    """Print the clean, minimal ASCII art TinyTorch logo."""
    console = get_console()

    if compact:
        print_compact_ascii_logo()
        return

    # Create styled logo text with proper Rich formatting
    logo_text = Text()

    # ============================================
    # TINYTORCH LOGO - EDIT HERE!
    # ============================================
    # To edit: Change the ASCII characters in logo_lines
    # Add/remove spaces at the beginning of each line to adjust positioning

    logo_lines = [
        # Flames positioned above T and H
        "    🔥                                     🔥",
        "    ████████╗ ██████╗ ██████╗  ██████╗██╗  ██╗",
        "    ╚T═██╔══╝██╔═══██╗██╔══██╗██╔════╝██║  ██║",
        "     I ██║   ██║   ██║██████╔╝██║     ███████║",
        "     N ██║   ██║   ██║██╔══██╗██║     ██╔══██║",
        "     Y ██║   ╚██████╔╝██║  ██║╚██████╗██║  ██║",
        "       ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝"
    ]

    # ============================================
    # COLOR CONFIGURATION - Uses Theme constants
    # ============================================
    FLAME_COLOR = Theme.BRAND_FLAME     # Color for 🔥 emoji
    TINY_COLOR = Theme.BRAND_ACCENT     # Color for "tiny" text
    TORCH_COLOR = Theme.BRAND_PRIMARY   # Color for "TORCH" text
    TAGLINE_COLOR = Theme.BRAND_ACCENT  # Color for tagline

    # Process and apply colors to each line
    for i, line in enumerate(logo_lines):
        if i == 0:  # Flame line
            logo_text.append(line, style=FLAME_COLOR)
        elif i >= 1 and i <= 5:  # Lines with tiny letters (t,i,n,y) + TORCH
            # Color individual tiny letters within the line
            for char in line:
                if char in 'TINY':
                    logo_text.append(char, style=TINY_COLOR)
                else:
                    logo_text.append(char, style=TORCH_COLOR)
        else:  # Pure TORCH lines
            logo_text.append(line, style=TORCH_COLOR)
        logo_text.append("\n")

    # Add tagline with flame (aligned under TORCH)
    logo_text.append("\n           🔥 Don't import it. Build it.", style=TAGLINE_COLOR)
    logo_text.append("\n")

    # Combine logo and tagline
    full_content = Text()
    full_content.append(logo_text)

    # Display centered with rich styling
    console.print()
    console.print(Panel(
        Align.center(full_content),
        border_style=Theme.BORDER_DEFAULT,
        padding=(1, 2)
    ))
    console.print()

def print_compact_ascii_logo():
    """Print the compact ASCII art TinyTorch logo - same as main logo now."""
    # Just use the main logo since it's already compact and clean
    print_ascii_logo(compact=False)

def print_error(message: str, title: str = "Error"):
    """Print an error message with consistent formatting."""
    console = get_console()
    console.print(Panel(f"[{Theme.ERROR}]❌ {message}[/{Theme.ERROR}]", title=title, border_style=Theme.BORDER_ERROR))

def print_success(message: str, title: str = "Success"):
    """Print a success message with consistent formatting."""
    console = get_console()
    console.print(Panel(f"[{Theme.SUCCESS}]✅ {message}[/{Theme.SUCCESS}]", title=title, border_style=Theme.BORDER_SUCCESS))

def print_warning(message: str, title: str = "Warning"):
    """Print a warning message with consistent formatting."""
    console = get_console()
    console.print(Panel(f"[{Theme.WARNING}]⚠️ {message}[/{Theme.WARNING}]", title=title, border_style=Theme.BORDER_WARNING))

def print_info(message: str, title: str = "Info"):
    """Print an info message with consistent formatting."""
    console = get_console()
    console.print(Panel(f"[{Theme.INFO}]ℹ️ {message}[/{Theme.INFO}]", title=title, border_style=Theme.BORDER_INFO))
