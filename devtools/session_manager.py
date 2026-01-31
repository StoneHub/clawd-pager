"""
Session Manager - Records and replays development sessions.

Sessions are collections of events that can be:
- Started/stopped manually via dashboard
- Annotated with notes (e.g., "testing button B latency")
- Compressed and stored for later analysis
- Replayed to understand what happened

Usage:
    from devtools.session_manager import SessionManager

    mgr = SessionManager()
    mgr.start_session("Testing voice capture fix")

    # ... do stuff, events are captured by EventLogger ...

    session_id = mgr.end_session()
    print(f"Session saved: {session_id}")

    # Later: replay
    session = mgr.load_session(session_id)
    for event in session.events:
        print(event)
"""

import json
import gzip
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict, field

from .event_logger import EventLogger, EventSource, PagerEvent, get_logger


@dataclass
class SessionRecording:
    """A complete recorded development session."""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    notes: str = ""
    events: List[Dict[str, Any]] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)  # Paths to screenshot files
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'SessionRecording':
        return cls(**data)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate session duration."""
        if not self.end_time:
            return None
        start = datetime.fromisoformat(self.start_time)
        end = datetime.fromisoformat(self.end_time)
        return (end - start).total_seconds()

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def error_count(self) -> int:
        return sum(1 for e in self.events if e.get('event_type') == 'ERROR')


class SessionManager:
    """
    Manages recording and playback of development sessions.

    Sessions are stored as gzip-compressed JSON files in ~/.clawd/sessions/
    """

    def __init__(self, storage_dir: str = "~/.clawd/sessions",
                 event_logger: Optional[EventLogger] = None):
        """
        Initialize the session manager.

        Args:
            storage_dir: Directory to store session recordings
            event_logger: EventLogger instance (uses global singleton if not provided)
        """
        self.storage_dir = Path(storage_dir).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.event_logger = event_logger or get_logger()
        self.current_session: Optional[SessionRecording] = None
        self._recording = False

    @property
    def is_recording(self) -> bool:
        """Check if a session is currently being recorded."""
        return self._recording and self.current_session is not None

    def start_session(self, notes: str = "",
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start recording a new session.

        Args:
            notes: Description of what you're testing/working on
            metadata: Additional metadata (e.g., git branch, device state)

        Returns:
            The new session ID
        """
        if self.is_recording:
            # End current session before starting new one
            self.end_session()

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.current_session = SessionRecording(
            session_id=session_id,
            start_time=datetime.now().isoformat(timespec='milliseconds'),
            notes=notes,
            metadata=metadata or {}
        )

        self._recording = True

        # Log session start event
        self.event_logger.log(EventSource.USER, "SESSION_START", {
            "recording_session_id": session_id,
            "notes": notes
        })

        return session_id

    def add_note(self, note: str):
        """Add a note to the current session."""
        if self.current_session:
            timestamp = datetime.now().isoformat(timespec='milliseconds')
            self.current_session.notes += f"\n[{timestamp}] {note}"

            self.event_logger.log(EventSource.USER, "NOTE", {
                "note": note
            })

    def add_screenshot(self, path: str):
        """Add a screenshot path to the current session."""
        if self.current_session:
            self.current_session.screenshots.append(path)

    def add_event(self, event: PagerEvent):
        """Manually add an event to the session (used during replay)."""
        if self.current_session:
            self.current_session.events.append(event.to_dict())

    def end_session(self) -> Optional[str]:
        """
        End the current recording session and save to disk.

        Returns:
            The session ID if a session was active, None otherwise
        """
        if not self.current_session:
            return None

        self.current_session.end_time = datetime.now().isoformat(timespec='milliseconds')

        # Capture all events from the EventLogger for this session
        events = self.event_logger.get_session_events(
            self.event_logger.session_id
        )
        self.current_session.events = [e.to_dict() for e in events]

        # Save to disk
        self._save_session(self.current_session)

        session_id = self.current_session.session_id

        # Log session end
        self.event_logger.log(EventSource.USER, "SESSION_END", {
            "recording_session_id": session_id,
            "event_count": len(self.current_session.events),
            "duration_s": self.current_session.duration_seconds
        })

        self.current_session = None
        self._recording = False

        return session_id

    def _save_session(self, session: SessionRecording):
        """Save a session to compressed JSON file."""
        path = self.storage_dir / f"{session.session_id}.json.gz"
        with gzip.open(path, 'wt', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, indent=2)

    def load_session(self, session_id: str) -> SessionRecording:
        """
        Load a recorded session from disk.

        Args:
            session_id: The session ID to load

        Returns:
            SessionRecording object

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        path = self.storage_dir / f"{session_id}.json.gz"
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        with gzip.open(path, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        return SessionRecording.from_dict(data)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all recorded sessions with summary info.

        Returns:
            List of session summaries sorted by date (newest first)
        """
        sessions = []

        for path in sorted(self.storage_dir.glob("*.json.gz"), reverse=True):
            try:
                session = self.load_session(path.stem)
                sessions.append({
                    "session_id": session.session_id,
                    "start_time": session.start_time,
                    "end_time": session.end_time,
                    "duration_s": session.duration_seconds,
                    "event_count": session.event_count,
                    "error_count": session.error_count,
                    "notes": session.notes[:100] if session.notes else "",
                    "has_screenshots": len(session.screenshots) > 0
                })
            except Exception as e:
                # Skip corrupted files
                continue

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a recorded session.

        Args:
            session_id: The session ID to delete

        Returns:
            True if deleted, False if not found
        """
        path = self.storage_dir / f"{session_id}.json.gz"
        if path.exists():
            path.unlink()
            return True
        return False

    def get_session_timeline(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get a simplified timeline of events for visualization.

        Args:
            session_id: The session to get timeline for

        Returns:
            List of simplified event dicts with timestamp, type, and summary
        """
        session = self.load_session(session_id)
        timeline = []

        for event in session.events:
            summary = self._get_event_summary(event)
            timeline.append({
                "timestamp": event.get("timestamp"),
                "event_type": event.get("event_type"),
                "source": event.get("source"),
                "summary": summary
            })

        return timeline

    def _get_event_summary(self, event: Dict[str, Any]) -> str:
        """Generate a human-readable summary of an event."""
        event_type = event.get("event_type", "UNKNOWN")
        data = event.get("data", {})

        summaries = {
            "BUTTON_PRESS": lambda d: f"Button {d.get('button')} pressed",
            "BUTTON_RELEASE": lambda d: f"Button {d.get('button')} released ({d.get('duration_ms', 0):.0f}ms)",
            "MODE_CHANGE": lambda d: f"{d.get('from_mode')} -> {d.get('to_mode')}",
            "DISPLAY_UPDATE": lambda d: f"[{d.get('mode')}] {d.get('text', '')[:30]}...",
            "AUDIO_START": lambda d: "Voice capture started",
            "AUDIO_END": lambda d: f"Voice captured: {d.get('bytes_captured', 0)} bytes",
            "STT_RESULT": lambda d: f"Heard: \"{d.get('transcript', '')[:40]}...\"",
            "ERROR": lambda d: f"ERROR: {d.get('error_type')}: {d.get('message', '')[:30]}",
            "BUILD_START": lambda d: f"Building {d.get('yaml_file')}",
            "BUILD_END": lambda d: f"Build {'succeeded' if d.get('success') else 'FAILED'} ({d.get('duration_s', 0):.1f}s)",
            "OTA_START": lambda d: f"Uploading to {d.get('target_ip')}",
            "OTA_END": lambda d: f"Upload {'succeeded' if d.get('success') else 'FAILED'}",
        }

        if event_type in summaries:
            try:
                return summaries[event_type](data)
            except:
                pass

        return event_type

    def export_session_markdown(self, session_id: str) -> str:
        """
        Export a session as Markdown for documentation.

        Args:
            session_id: The session to export

        Returns:
            Markdown-formatted session report
        """
        session = self.load_session(session_id)

        md = f"""# Session Report: {session.session_id}

**Start**: {session.start_time}
**End**: {session.end_time or 'ongoing'}
**Duration**: {session.duration_seconds:.1f}s
**Events**: {session.event_count}
**Errors**: {session.error_count}

## Notes

{session.notes or '(none)'}

## Event Timeline

| Time | Type | Source | Summary |
|------|------|--------|---------|
"""

        for event in session.events:
            ts = event.get("timestamp", "")
            if "T" in ts:
                ts = ts.split("T")[1][:12]  # Just time portion
            summary = self._get_event_summary(event)
            md += f"| {ts} | {event.get('event_type')} | {event.get('source')} | {summary} |\n"

        return md


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global SessionManager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
