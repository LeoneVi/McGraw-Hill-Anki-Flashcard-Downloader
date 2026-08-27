"""Shared progress reporting for terminal and library workflows."""

from collections.abc import Callable


ProgressCallback = Callable[[str], None]


def report_progress(
    progress_callback: ProgressCallback | None,
    message: str,
) -> None:
    """Send one status message when a caller supplied a progress callback."""
    if progress_callback is not None:
        progress_callback(message)


class TerminalProgress:
    """Keep replacing one terminal line with the latest progress message."""

    def __init__(self) -> None:
        self._active = False
        self._line_width = 0

    def update(self, message: str) -> None:
        """Show the newest status immediately without filling the console."""
        self._active = True
        self._line_width = max(self._line_width, len(message))
        print(f"\r{message.ljust(self._line_width)}", end="", flush=True)

    def finish(self) -> None:
        """Finish the active progress line before normal output resumes."""
        if self._active:
            print()
            self._active = False
