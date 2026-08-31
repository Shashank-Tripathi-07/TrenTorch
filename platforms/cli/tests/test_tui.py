import asyncio
from platforms.cli.core.config import CLIConfig
from platforms.cli.tui.app import TrenTorchApp
from platforms.cli.tui.command import TUICommand


def test_tui_app_initialization():
    """Verify that the TUI app initializes, populates modules, and sets up tabs."""
    async def _runner():
        config = CLIConfig.from_project_root()
        app = TrenTorchApp(config=config, initial_module="01")

        async with app.run_test() as pilot:
            # Check title
            assert "Tren⚡️Torch" in app.TITLE

            # Check tabs exist
            tabs = app.query_one("#main-tabs")
            assert tabs is not None

            # Verify default active tab is modules
            assert tabs.active == "modules-tab"

            # Verify switching tabs via bindings
            await pilot.press("2")
            assert tabs.active == "milestones-tab"

            await pilot.press("3")
            assert tabs.active == "benchmarks-tab"

            await pilot.press("4")
            assert tabs.active == "health-tab"

            await pilot.press("1")
            assert tabs.active == "modules-tab"

    asyncio.run(_runner())


def test_tui_command_registration():
    """Verify TUICommand exposes the expected metadata."""
    config = CLIConfig.from_project_root()
    cmd = TUICommand(config)
    assert cmd.name == "tui"
    assert "interactive" in cmd.description.lower()

