# Milestone System API

## Source of Truth

`tren.commands.milestone.MILESTONE_SCRIPTS` is the canonical milestone table.
It defines IDs, names, required modules, scripts, descriptions, and historical
context.

`tests/milestones/milestone_tracker.py` is a compatibility layer for older test
hooks. It imports `MILESTONE_SCRIPTS` rather than maintaining a separate milestone
taxonomy.

## State Files

The current CLI state lives under `.tren/`:

- `.tren/progress.json`: module progress, including `completed_modules`
- `.tren/milestones.json`: milestone readiness and completion state

Legacy code should not write milestone state outside the project `.tren/` directory.

## Public Compatibility Functions

### `check_module_export(module_name: str, console=None) -> dict`

Marks a completed module in `.tren/progress.json`, checks whether any milestones
are newly ready, writes `.tren/milestones.json`, and returns:

```python
{
    "newly_unlocked": ["01"],
    "messages": ["Milestone ready to run ..."]
}
```

### `show_progress()`

Prints milestone readiness based on `.tren/progress.json` and
`.tren/milestones.json`.

### `list_tests()`

Prints ready milestone run commands, such as:

```bash
tren milestone run 03
```

## CLI Integration

Current user-facing commands are implemented in `tren/commands/milestone.py`:

```bash
tren milestone list
tren milestone status
tren milestone info 03
tren milestone run 03
```

`tren module complete` also checks milestone readiness after recording module
completion. That code should use the canonical `MILESTONE_SCRIPTS` table, not a
duplicated list of requirements.

## Adding or Changing Milestones

1. Update `MILESTONE_SCRIPTS`.
2. Add or rename scripts under `milestones/`.
3. Update `test_milestones_smoke.py` for import/model construction coverage.
4. Update `test_milestones_run.py` for release-run coverage.
5. Update milestone READMEs.

Keep command examples singular: use `tren milestone`.
