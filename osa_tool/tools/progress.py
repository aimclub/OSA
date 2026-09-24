"""Rich progress reporting shared by focused command-line tools."""

from __future__ import annotations

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn


class RichStageProgress:
    """Render one bounded, stage-oriented progress task to stderr."""

    def __init__(self, initial_description: str) -> None:
        self._initial_description = initial_description
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            console=Console(stderr=True),
            transient=False,
        )
        self._task_id: TaskID | None = None

    def __enter__(self) -> "RichStageProgress":
        self._progress.start()
        self._task_id = self._progress.add_task(self._initial_description, total=100)
        return self

    def __exit__(self, *_: object) -> None:
        self._progress.stop()

    def update(self, description: str, fraction: float) -> None:
        if self._task_id is None:
            raise RuntimeError("RichStageProgress must be entered before updates")
        self._progress.update(
            self._task_id,
            description=description,
            completed=min(max(fraction, 0.0), 1.0) * 100,
        )
