"""
TrenTorch Interactive Textual Terminal User Interface (TUI).
"""

import json
import os
import subprocess
import sys
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    OptionList,
    ProgressBar,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)
from textual.worker import get_current_worker

from platforms.cli.core.config import CLIConfig
from platforms.cli.core.modules import get_all_module_metadata, get_module_mapping, normalize_module_number
from platforms.cli.processes.milestone.constants import MILESTONE_SCRIPTS

MODULE_STAGES = {
    "Part 1: Foundations": ["01", "02", "03", "04", "05"],
    "Part 2: Deep Learning Core": ["06", "07", "08", "09"],
    "Part 3: Architecture & Scale": ["10", "11", "12", "13"],
    "Part 4: Systems Engineering": ["14", "15", "16", "17", "18", "19", "20"],
}

TUI_CSS = """
Screen {
    background: #0d0f17;
    color: #e2e8f0;
}

Header {
    background: #141724;
    color: #38bdf8;
    dock: top;
    height: 3;
}

Footer {
    background: #141724;
    color: #94a3b8;
    dock: bottom;
    height: 1;
}

TabbedContent {
    height: 100%;
}

TabPane {
    padding: 1 1;
}

.box-panel {
    background: #141726;
    border: round #334155;
    padding: 1;
    height: 100%;
}

.box-panel-focus {
    border: round #818cf8;
}

#module-sidebar {
    width: 38;
    height: 100%;
    margin-right: 1;
}

#module-content {
    width: 1fr;
    height: 100%;
}

#module-inspector {
    height: auto;
    max-height: 14;
    background: #181c2f;
    border: round #475569;
    padding: 1;
    margin-bottom: 1;
}

#action-bar {
    height: 3;
    margin-bottom: 1;
    align: left middle;
}

#action-bar Button {
    margin-right: 1;
    min-width: 14;
    border: none;
    height: 3;
}

.btn-start {
    background: #0284c7;
    color: #ffffff;
}

.btn-start:hover {
    background: #38bdf8;
}

.btn-test {
    background: #059669;
    color: #ffffff;
}

.btn-test:hover {
    background: #10b981;
}

.btn-complete {
    background: #7c3aed;
    color: #ffffff;
}

.btn-complete:hover {
    background: #a855f7;
}

.btn-jupyter {
    background: #d97706;
    color: #ffffff;
}

.btn-jupyter:hover {
    background: #f59e0b;
}

.btn-reset {
    background: #b91c1c;
    color: #ffffff;
}

.btn-reset:hover {
    background: #ef4444;
}

#log-container {
    height: 1fr;
    background: #090a10;
    border: round #334155;
    padding: 0 1;
}

RichLog {
    background: transparent;
    color: #f1f5f9;
    scrollbar-gutter: stable;
}

.section-title {
    color: #f59e0b;
    text-style: bold;
    margin-bottom: 1;
}

.dim-label {
    color: #64748b;
}

.stat-val {
    color: #38bdf8;
    text-style: bold;
}

#milestones-list {
    width: 42;
    height: 100%;
    margin-right: 1;
}

#milestone-detail {
    width: 1fr;
    height: 100%;
    padding: 1;
}

#health-table {
    height: auto;
    max-height: 20;
    margin-top: 1;
}
"""


class TrenTorchApp(App):
    """TrenTorch Interactive Textual Terminal Application."""

    TITLE = "Tren⚡️Torch Interactive Dashboard"
    SUB_TITLE = "Machine Learning Systems Engineering from Scratch"
    CSS = TUI_CSS

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("t", "run_test", "Test (t)"),
        Binding("c", "run_complete", "Complete (c)"),
        Binding("s", "run_start", "Start (s)"),
        Binding("j", "run_jupyter", "Jupyter (j)"),
        Binding("r", "run_reset", "Reset (r)"),
        Binding("1", "show_tab('modules')", "Modules (1)"),
        Binding("2", "show_tab('milestones')", "Milestones (2)"),
        Binding("3", "show_tab('benchmarks')", "Benchmarks (3)"),
        Binding("4", "show_tab('health')", "Health (4)"),
    ]

    def __init__(self, config: CLIConfig | None = None, initial_module: str | None = None):
        super().__init__()
        self.config = config or CLIConfig.from_project_root()
        self.module_mapping = get_module_mapping()
        self.module_metadata = get_all_module_metadata()
        self.initial_module = normalize_module_number(initial_module) if initial_module else "01"
        self.current_module_num = self.initial_module
        self.progress_data: dict[str, Any] = self._load_progress()
        self.is_task_running = False

    def _load_progress(self) -> dict[str, Any]:
        """Load progress.json data."""
        p_file = self.config.project_root / "user_data" / "progress.json"
        if p_file.exists():
            try:
                with open(p_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "started_modules": [],
            "completed_modules": [],
            "last_worked": None,
            "last_completed": None,
        }

    def compose(self) -> ComposeResult:
        """Compose the main layout."""
        yield Header(show_clock=True)
        with TabbedContent(id="main-tabs", initial="modules-tab"):
            # TAB 1: MODULES
            with TabPane("📦 20 Modules", id="modules-tab"):
                with Horizontal():
                    # Sidebar
                    with Vertical(id="module-sidebar", classes="box-panel"):
                        yield Label("📚 Curriculum Navigator", classes="section-title")
                        yield OptionList(id="modules-option-list")
                        yield Label("Progress:", classes="dim-label")
                        yield ProgressBar(id="overall-progress", total=20, show_percentage=True)

                    # Main Module Workspace
                    with Vertical(id="module-content"):
                        with Vertical(id="module-inspector"):
                            yield Static(id="module-header-text")
                            yield Static(id="module-desc-text")
                            yield Static(id="module-details-text")

                        # Action bar buttons
                        with Horizontal(id="action-bar"):
                            yield Button("▶ Start [s]", id="btn-start", classes="btn-start")
                            yield Button("🧪 Test [t]", id="btn-test", classes="btn-test")
                            yield Button("🚀 Complete [c]", id="btn-complete", classes="btn-complete")
                            yield Button("🪐 Jupyter [j]", id="btn-jupyter", classes="btn-jupyter")
                            yield Button("🔄 Reset [r]", id="btn-reset", classes="btn-reset")

                        # Live execution terminal
                        with Vertical(id="log-container"):
                            with Horizontal(classes="log-header"):
                                yield Label("📟 Live Execution Terminal", classes="dim-label")
                            yield RichLog(id="execution-log", wrap=True, highlight=True, markup=True)

            # TAB 2: MILESTONES
            with TabPane("🏆 Milestones", id="milestones-tab"):
                with Horizontal():
                    with Vertical(id="milestones-list", classes="box-panel"):
                        yield Label("🏛 Historical ML Milestones", classes="section-title")
                        yield OptionList(id="milestone-option-list")
                    with Vertical(id="milestone-detail", classes="box-panel"):
                        yield Static(id="milestone-detail-text")
                        with Horizontal():
                            yield Button(
                                "🚀 Run Milestone Script", id="btn-run-milestone", classes="btn-complete"
                            )
                        yield Label("\nMilestone Execution Output:", classes="dim-label")
                        yield RichLog(id="milestone-log", wrap=True, highlight=True, markup=True)

            # TAB 3: BENCHMARKS & OLYMPICS
            with TabPane("⚡ Benchmarks & Olympics", id="benchmarks-tab"):
                with Vertical(classes="box-panel"):
                    yield Label("⚡ TrenTorch Op Benchmarks & Olympics", classes="section-title")
                    yield Static(
                        "Benchmark your custom TrenTorch implementation against NumPy and reference baselines.\n"
                        "Measure throughput, latency, memory footprint, and numerical parity."
                    )
                    with Horizontal():
                        yield Button("🏃 Run Op Benchmarks", id="btn-run-benchmarks", classes="btn-start")
                        yield Button("🥇 Run Olympics Suite", id="btn-run-olympics", classes="btn-complete")
                    yield RichLog(id="benchmark-log", wrap=True, highlight=True, markup=True)

            # TAB 4: SYSTEM HEALTH
            with TabPane("💚 System Health", id="health-tab"):
                with Vertical(classes="box-panel"):
                    yield Label("💚 Environment Health & Diagnostic Deck", classes="section-title")
                    yield Static(id="health-summary-text")
                    yield DataTable(id="health-table")
                    with Horizontal():
                        yield Button("🔄 Refresh Diagnostics", id="btn-refresh-health", classes="btn-start")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize data on mount."""
        self._populate_module_list()
        self._populate_milestone_list()
        self._update_module_details()
        self._update_health_tab()
        self._log("⚡ [bold green]Welcome to TrenTorch Interactive Dashboard![/bold green]")
        self._log(
            "Press [bold cyan][t][/bold cyan] to test current module, "
            "[bold purple][c][/bold purple] to complete/export, "
            "or use arrow keys to navigate."
        )

    def _log(self, message: str, log_id: str = "execution-log") -> None:
        """Write line to specified RichLog."""
        try:
            log_widget = self.query_one(f"#{log_id}", RichLog)
            log_widget.write(message)
        except Exception:
            pass

    def _populate_module_list(self) -> None:
        """Populate the module list widget."""
        option_list = self.query_one("#modules-option-list", OptionList)
        option_list.clear_options()

        completed = set(self.progress_data.get("completed_modules", []))
        started = set(self.progress_data.get("started_modules", []))

        initial_index = 0
        current_idx = 0

        for stage_name, mod_nums in MODULE_STAGES.items():
            for num in mod_nums:
                folder_name = self.module_mapping.get(num, f"{num}_module")
                display_title = (
                    folder_name.split("_", 1)[1].replace("_", " ").title()
                    if "_" in folder_name
                    else folder_name
                )

                if num in completed:
                    badge = "[green]✓ DONE[/green]"
                elif num in started:
                    badge = "[cyan]▶ WORK[/cyan]"
                else:
                    badge = "[dim]○ TODO[/dim]"

                line = f"{badge} {num} {display_title}"
                option_list.add_option(line)

                if num == self.current_module_num:
                    initial_index = current_idx
                current_idx += 1

        option_list.highlighted = initial_index
        prog_bar = self.query_one("#overall-progress", ProgressBar)
        prog_bar.progress = len(completed)

    def _populate_milestone_list(self) -> None:
        """Populate the historical milestone options."""
        option_list = self.query_one("#milestone-option-list", OptionList)
        option_list.clear_options()

        for m_id, m_data in sorted(MILESTONE_SCRIPTS.items()):
            emoji = m_data.get("emoji", "🏆")
            name = m_data.get("name", f"Milestone {m_id}")
            title = m_data.get("title", "")
            option_list.add_option(f"{emoji} {name} - {title}")

        option_list.highlighted = 0
        self._update_milestone_details(0)

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Handle list navigation."""
        if event.option_list.id == "modules-option-list":
            # Map index to module number
            all_nums = []
            for nums in MODULE_STAGES.values():
                all_nums.extend(nums)
            if 0 <= event.option_index < len(all_nums):
                self.current_module_num = all_nums[event.option_index]
                self._update_module_details()
        elif event.option_list.id == "milestone-option-list":
            self._update_milestone_details(event.option_index)

    def _update_module_details(self) -> None:
        """Update the inspector panel with the current module info."""
        num = self.current_module_num
        folder_name = self.module_mapping.get(num, f"{num}_module")
        meta = self.module_metadata.get(folder_name)

        header_widget = self.query_one("#module-header-text", Static)
        desc_widget = self.query_one("#module-desc-text", Static)
        details_widget = self.query_one("#module-details-text", Static)

        # Find stage
        stage_name = "Unknown Stage"
        for stg, nums in MODULE_STAGES.items():
            if num in nums:
                stage_name = stg
                break

        title = meta.title if meta else folder_name.replace("_", " ").title()
        desc = meta.description if meta else "Build and test this machine learning module from scratch."

        is_completed = num in self.progress_data.get("completed_modules", [])
        is_started = num in self.progress_data.get("started_modules", [])
        status_str = (
            "[bold green]COMPLETED[/bold green]"
            if is_completed
            else ("[bold cyan]IN PROGRESS[/bold cyan]" if is_started else "[dim]NOT STARTED[/dim]")
        )

        header_widget.update(
            f"[bold #38bdf8]Module {num}: {title}[/bold #38bdf8]  • {status_str} •  [dim]({stage_name})[/dim]"
        )
        desc_widget.update(f"[italic #94a3b8]{desc}[/italic #94a3b8]")

        src_py = self.config.modules_dir / folder_name / f"{folder_name}.py"
        test_py = self.config.project_root / "tests" / f"test_{folder_name}.py"

        details_widget.update(
            f"[dim]Source Stub:[/dim] [cyan]{src_py.relative_to(self.config.project_root)}[/cyan]  |  "
            f"[dim]Pytest File:[/dim] [cyan]{test_py.relative_to(self.config.project_root) if test_py.exists() else 'inline in .py'}[/cyan]"
        )

    def _update_milestone_details(self, index: int) -> None:
        """Update milestone details view."""
        milestone_keys = sorted(MILESTONE_SCRIPTS.keys())
        if index < 0 or index >= len(milestone_keys):
            return

        m_key = milestone_keys[index]
        m_data = MILESTONE_SCRIPTS[m_key]

        req_mods = m_data.get("required_modules", [])
        req_str = ", ".join(f"{int(m):02d}" for m in req_mods)

        detail_text = (
            f"[bold #f59e0b]{m_data.get('emoji', '🏆')} {m_data.get('name')} - {m_data.get('title')}[/bold #f59e0b]\n\n"
            f"[bold #38bdf8]Historical Context:[/bold #38bdf8] {m_data.get('historical_context', 'N/A')}\n"
            f"[bold #38bdf8]Description:[/bold #38bdf8] {m_data.get('description', 'N/A')}\n"
            f"[bold #38bdf8]Required Modules:[/bold #38bdf8] [yellow]{req_str}[/yellow]\n"
            f"[bold #38bdf8]Script Path:[/bold #38bdf8] [dim]{m_data.get('script', m_data.get('scripts', 'N/A'))}[/dim]"
        )
        self.query_one("#milestone-detail-text", Static).update(detail_text)

    def _update_health_tab(self) -> None:
        """Update the health diagnostic table."""
        summary = self.query_one("#health-summary-text", Static)
        table = self.query_one("#health-table", DataTable)
        table.clear(columns=True)

        in_venv = sys.prefix != sys.base_prefix or os.environ.get("VIRTUAL_ENV") is not None
        summary.update(
            f"[bold cyan]Python Version:[/bold cyan] {sys.version.split()[0]}  |  "
            f"[bold cyan]Environment:[/bold cyan] {'[green]Active Virtualenv[/green]' if in_venv else '[yellow]System Python[/yellow]'}  |  "
            f"[bold cyan]Project Root:[/bold cyan] [dim]{self.config.project_root}[/dim]"
        )

        table.add_columns("Component", "Status", "Details")
        table.add_row(
            "Python Version",
            "✅ PASS",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
        table.add_row("Virtualenv", "✅ ACTIVE" if in_venv else "⚠️ SYSTEM", str(sys.prefix))

        # Check core packages
        for pkg in ["numpy", "rich", "textual", "yaml", "pytest"]:
            try:
                mod = __import__(pkg)
                ver = getattr(mod, "__version__", "Installed")
                table.add_row(f"Package: {pkg}", "✅ OK", str(ver))
            except ImportError:
                table.add_row(f"Package: {pkg}", "❌ MISSING", "Install via pip")

        # Check exported package
        tp_path = self.config.project_root / "data" / "trentorch"
        table.add_row(
            "Exported Library (data/trentorch)",
            "✅ FOUND" if tp_path.exists() else "⚠️ NOT EXPORTED",
            f"{len(list(tp_path.glob('*.py')))} modules exported"
            if tp_path.exists()
            else "Run 'tren dev export --all'",
        )

    # ------------------ ASYNC WORKERS FOR ACTIONS ------------------

    @work(exclusive=True, thread=True)
    def _run_subprocess_worker(
        self, cmd: list[str], log_widget_id: str = "execution-log", title: str = "Task"
    ) -> None:
        """Run subprocess in a background worker and stream output to RichLog.

        ``exclusive=True`` means a new run cancels the previous one; the
        cancellation check inside the read loop is what actually stops the
        subprocess, since worker threads cannot be force-killed.
        """
        worker = get_current_worker()
        self.is_task_running = True
        self._log(f"\n[bold #38bdf8]─── {title} ───[/bold #38bdf8]", log_widget_id)
        self._log(f"[dim]$ {' '.join(cmd)}[/dim]\n", log_widget_id)

        process = None
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["TITO_ALLOW_SYSTEM"] = "1"
            env["TREN_ALLOW_SYSTEM"] = "1"

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.config.project_root),
                env=env,
            )

            if process.stdout:
                for line in process.stdout:
                    if worker.is_cancelled:
                        process.kill()
                        self._log("[yellow]⚠️ Task cancelled.[/yellow]", log_widget_id)
                        return
                    self._log(line.rstrip(), log_widget_id)

            process.wait()
            rc = process.returncode
            if rc == 0:
                self._log(
                    f"[bold green]✔ {title} Completed Successfully (exit code 0)[/bold green]", log_widget_id
                )
            else:
                self._log(f"[bold red]✘ {title} Failed (exit code {rc})[/bold red]", log_widget_id)

        except Exception as e:
            self._log(f"[bold red]Error executing command: {e}[/bold red]", log_widget_id)
            if process is not None:
                process.kill()
        finally:
            self.is_task_running = False
            # Reload progress in case it updated
            self.progress_data = self._load_progress()
            self.call_from_thread(self._populate_module_list)
            self.call_from_thread(self._update_module_details)

    # ------------------ BUTTON / KEY ACTION HANDLERS ------------------

    def action_run_test(self) -> None:
        """Run tests for the current module."""
        num = self.current_module_num
        folder_name = self.module_mapping.get(num, f"{num}_module")
        cmd = [sys.executable, "-m", "platforms.cli.main", "module", "test", num, "--verbose"]
        self._run_subprocess_worker(cmd, "execution-log", f"Testing Module {num} ({folder_name})")

    def action_run_complete(self) -> None:
        """Complete & export current module."""
        num = self.current_module_num
        cmd = [sys.executable, "-m", "platforms.cli.main", "module", "complete", num]
        self._run_subprocess_worker(cmd, "execution-log", f"Completing & Exporting Module {num}")

    def action_run_start(self) -> None:
        """Start current module."""
        num = self.current_module_num
        cmd = [sys.executable, "-m", "platforms.cli.main", "module", "start", num, "--no-jupyter"]
        self._run_subprocess_worker(cmd, "execution-log", f"Initializing Module {num} Stub")

    def action_run_jupyter(self) -> None:
        """Open Jupyter for current module."""
        num = self.current_module_num
        self._log(f"[cyan]🚀 Launching Jupyter for Module {num}...[/cyan]")
        cmd = [sys.executable, "-m", "platforms.cli.main", "module", "view", num]
        self._run_subprocess_worker(cmd, "execution-log", f"Jupyter Launcher: Module {num}")

    def action_run_reset(self) -> None:
        """Reset current module stub."""
        num = self.current_module_num
        cmd = [sys.executable, "-m", "platforms.cli.main", "module", "reset", num, "--force"]
        self._run_subprocess_worker(cmd, "execution-log", f"Resetting Module {num}")

    def action_show_tab(self, tab_name: str) -> None:
        """Switch tab programmatically."""
        tab_map = {
            "modules": "modules-tab",
            "milestones": "milestones-tab",
            "benchmarks": "benchmarks-tab",
            "health": "health-tab",
        }
        target = tab_map.get(tab_name)
        if target:
            self.query_one("#main-tabs", TabbedContent).active = target

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        btn_id = event.button.id
        if btn_id == "btn-start":
            self.action_run_start()
        elif btn_id == "btn-test":
            self.action_run_test()
        elif btn_id == "btn-complete":
            self.action_run_complete()
        elif btn_id == "btn-jupyter":
            self.action_run_jupyter()
        elif btn_id == "btn-reset":
            self.action_run_reset()
        elif btn_id == "btn-run-milestone":
            opt_list = self.query_one("#milestone-option-list", OptionList)
            m_keys = sorted(MILESTONE_SCRIPTS.keys())
            if 0 <= opt_list.highlighted < len(m_keys):
                m_id = m_keys[opt_list.highlighted]
                cmd = [sys.executable, "-m", "platforms.cli.main", "milestone", "run", m_id]
                self._run_subprocess_worker(cmd, "milestone-log", f"Milestone {m_id} Execution")
        elif btn_id == "btn-run-benchmarks":
            cmd = [sys.executable, "-m", "platforms.cli.main", "benchmark", "run"]
            self._run_subprocess_worker(cmd, "benchmark-log", "Op Benchmarking")
        elif btn_id == "btn-run-olympics":
            cmd = [sys.executable, "-m", "platforms.cli.main", "olympics"]
            self._run_subprocess_worker(cmd, "benchmark-log", "TrenTorch Olympics Challenge")
        elif btn_id == "btn-refresh-health":
            self._update_health_tab()


def launch_tui(config: CLIConfig | None = None, initial_module: str | None = None) -> int:
    """Launch the interactive TrenTorch TUI application."""
    app = TrenTorchApp(config=config, initial_module=initial_module)
    app.run()
    return 0


if __name__ == "__main__":
    launch_tui()
