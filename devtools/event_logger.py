"""
Event Logger - Captures and persists all pager events to SQLite.

This is the foundation of the observability system. Every button press,
mode change, API call, and error gets timestamped and stored for
later analysis and session replay.

Usage:
    from devtools import EventLogger, EventSource

    logger = EventLogger()
    logger.log(EventSource.DEVICE, "BUTTON_PRESS", {"button": "A"})

    # Query events
    events = logger.get_recent_events(100)
    sessions = logger.list_sessions()
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading


class EventSource(Enum):
    """Where the event originated."""
    DEVICE = "device"      # From the M5StickC Plus (via ESPHome API)
    BRIDGE = "bridge"      # From the Python bridge
    USER = "user"          # From dev scripts or manual actions
    DASHBOARD = "dashboard"  # From the web dashboard


@dataclass
class PagerEvent:
    """A single timestamped event in the pager system."""
    timestamp: str
    session_id: str
    source: str
    event_type: str
    data: Dict[str, Any]
    sequence: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row: tuple) -> 'PagerEvent':
        """Create event from database row."""
        return cls(
            timestamp=row[1],
            session_id=row[2],
            source=row[3],
            event_type=row[4],
            data=json.loads(row[5]) if row[5] else {},
            sequence=row[6]
        )


class EventLogger:
    """
    SQLite-based event logger for the Clawd Pager system.

    Stores all events with timestamps for:
    - Post-mortem debugging
    - Session replay
    - Usage pattern analysis
    - AI assistant context
    """

    # Event types we track
    EVENT_TYPES = {
        # Device events (from ESPHome)
        "BUTTON_PRESS": "Button pressed",
        "BUTTON_RELEASE": "Button released (includes duration)",
        "MODE_CHANGE": "Display mode changed",
        "BOOT": "Device booted",
        "WIFI_CONNECT": "WiFi connected",
        "WIFI_DISCONNECT": "WiFi disconnected",

        # Bridge events (from Python)
        "DISPLAY_UPDATE": "Display text/mode updated",
        "API_CALL": "ESPHome service called",
        "AUDIO_START": "Voice capture started",
        "AUDIO_END": "Voice capture ended",
        "STT_RESULT": "Speech-to-text result",
        "TELEGRAM_SEND": "Message sent to Telegram",
        "ERROR": "An error occurred",
        "CONNECT": "Bridge connected to device",
        "DISCONNECT": "Bridge disconnected from device",

        # User events (from dev scripts)
        "BUILD_START": "ESPHome compile started",
        "BUILD_END": "ESPHome compile finished",
        "OTA_START": "OTA upload started",
        "OTA_END": "OTA upload finished",
        "SESSION_START": "Recording session started",
        "SESSION_END": "Recording session ended",
        "NOTE": "User added a note",
    }

    def __init__(self, db_path: str = "~/.clawd/pager_events.db"):
        """
        Initialize the event logger.

        Args:
            db_path: Path to SQLite database (will be created if doesn't exist)
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate session ID based on start time
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.sequence = 0
        self._lock = threading.Lock()

        # Initialize database
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

        # Log session start
        self.log(EventSource.BRIDGE, "SESSION_START", {
            "session_id": self.session_id,
            "pid": os.getpid()
        })

    def _init_db(self):
        """Create database schema if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                data JSON,
                sequence INTEGER NOT NULL
            )
        """)

        # Indexes for fast querying
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session
            ON events(session_id)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON events(timestamp)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type
            ON events(event_type)
        """)

        self.conn.commit()

    def log(self, source: EventSource, event_type: str,
            data: Optional[Dict[str, Any]] = None) -> PagerEvent:
        """
        Log an event to the database.

        Args:
            source: Where the event came from (EventSource enum)
            event_type: Type of event (e.g., "BUTTON_PRESS", "MODE_CHANGE")
            data: Additional event data as a dictionary

        Returns:
            The created PagerEvent
        """
        with self._lock:
            self.sequence += 1

            event = PagerEvent(
                timestamp=datetime.now().isoformat(timespec='milliseconds'),
                session_id=self.session_id,
                source=source.value,
                event_type=event_type,
                data=data or {},
                sequence=self.sequence
            )

            self.conn.execute(
                """INSERT INTO events
                   (timestamp, session_id, source, event_type, data, sequence)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (event.timestamp, event.session_id, event.source,
                 event.event_type, json.dumps(event.data), event.sequence)
            )
            self.conn.commit()

            return event

    def log_error(self, error_type: str, message: str,
                  source: EventSource = EventSource.BRIDGE,
                  stack: Optional[str] = None) -> PagerEvent:
        """Convenience method for logging errors."""
        return self.log(source, "ERROR", {
            "error_type": error_type,
            "message": message,
            "stack": stack
        })

    def get_session_events(self, session_id: Optional[str] = None) -> List[PagerEvent]:
        """
        Get all events for a session.

        Args:
            session_id: Session to query (defaults to current session)

        Returns:
            List of PagerEvent objects ordered by sequence
        """
        sid = session_id or self.session_id
        cursor = self.conn.execute(
            """SELECT * FROM events
               WHERE session_id = ?
               ORDER BY sequence""",
            (sid,)
        )
        return [PagerEvent.from_row(row) for row in cursor.fetchall()]

    def get_recent_events(self, limit: int = 100,
                          event_type: Optional[str] = None) -> List[PagerEvent]:
        """
        Get the most recent events across all sessions.

        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type (optional)

        Returns:
            List of PagerEvent objects, newest first
        """
        if event_type:
            cursor = self.conn.execute(
                """SELECT * FROM events
                   WHERE event_type = ?
                   ORDER BY id DESC LIMIT ?""",
                (event_type, limit)
            )
        else:
            cursor = self.conn.execute(
                """SELECT * FROM events
                   ORDER BY id DESC LIMIT ?""",
                (limit,)
            )
        return [PagerEvent.from_row(row) for row in cursor.fetchall()]

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all recorded sessions with summary info.

        Returns:
            List of session summaries with start/end times and event counts
        """
        cursor = self.conn.execute("""
            SELECT
                session_id,
                MIN(timestamp) as start_time,
                MAX(timestamp) as end_time,
                COUNT(*) as event_count,
                SUM(CASE WHEN event_type = 'ERROR' THEN 1 ELSE 0 END) as error_count
            FROM events
            GROUP BY session_id
            ORDER BY start_time DESC
        """)

        return [
            {
                "session_id": row[0],
                "start_time": row[1],
                "end_time": row[2],
                "event_count": row[3],
                "error_count": row[4]
            }
            for row in cursor.fetchall()
        ]

    def get_event_counts_by_type(self, session_id: Optional[str] = None) -> Dict[str, int]:
        """Get count of each event type for analysis."""
        sid = session_id or self.session_id
        cursor = self.conn.execute(
            """SELECT event_type, COUNT(*) as count
               FROM events
               WHERE session_id = ?
               GROUP BY event_type
               ORDER BY count DESC""",
            (sid,)
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    def search_events(self, query: str, limit: int = 50) -> List[PagerEvent]:
        """
        Search events by text in data field.

        Args:
            query: Text to search for in event data
            limit: Maximum results

        Returns:
            Matching events
        """
        cursor = self.conn.execute(
            """SELECT * FROM events
               WHERE data LIKE ?
               ORDER BY id DESC LIMIT ?""",
            (f'%{query}%', limit)
        )
        return [PagerEvent.from_row(row) for row in cursor.fetchall()]

    def close(self):
        """Close the database connection."""
        self.log(EventSource.BRIDGE, "SESSION_END", {
            "session_id": self.session_id,
            "total_events": self.sequence
        })
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Singleton instance for easy access
_logger_instance: Optional[EventLogger] = None


def get_logger() -> EventLogger:
    """Get or create the global EventLogger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = EventLogger()
    return _logger_instance


# Convenience functions for common events
def log_button_press(button: str, mode: str):
    """Log a button press event."""
    get_logger().log(EventSource.DEVICE, "BUTTON_PRESS", {
        "button": button,
        "display_mode": mode
    })


def log_button_release(button: str, duration_ms: float):
    """Log a button release event."""
    get_logger().log(EventSource.DEVICE, "BUTTON_RELEASE", {
        "button": button,
        "duration_ms": duration_ms
    })


def log_mode_change(from_mode: str, to_mode: str):
    """Log a display mode change."""
    get_logger().log(EventSource.DEVICE, "MODE_CHANGE", {
        "from_mode": from_mode,
        "to_mode": to_mode
    })


def log_display_update(text: str, mode: str):
    """Log a display update."""
    get_logger().log(EventSource.BRIDGE, "DISPLAY_UPDATE", {
        "text": text[:100],  # Truncate for storage
        "mode": mode
    })


def log_api_call(service_name: str, args: Dict[str, Any]):
    """Log an ESPHome API service call."""
    get_logger().log(EventSource.BRIDGE, "API_CALL", {
        "service": service_name,
        "args": args
    })


def log_audio_start():
    """Log voice capture start."""
    get_logger().log(EventSource.DEVICE, "AUDIO_START", {
        "sample_rate": 16000
    })


def log_audio_end(bytes_captured: int, duration_ms: float):
    """Log voice capture end."""
    get_logger().log(EventSource.DEVICE, "AUDIO_END", {
        "bytes_captured": bytes_captured,
        "duration_ms": duration_ms
    })


def log_stt_result(transcript: str, confidence: Optional[float] = None):
    """Log speech-to-text result."""
    get_logger().log(EventSource.BRIDGE, "STT_RESULT", {
        "transcript": transcript,
        "confidence": confidence
    })


def log_build_start(yaml_file: str):
    """Log ESPHome build start."""
    get_logger().log(EventSource.USER, "BUILD_START", {
        "yaml_file": yaml_file
    })


def log_build_end(success: bool, duration_s: float, firmware_size: Optional[int] = None):
    """Log ESPHome build completion."""
    get_logger().log(EventSource.USER, "BUILD_END", {
        "success": success,
        "duration_s": duration_s,
        "firmware_size": firmware_size
    })


def log_ota_start(target_ip: str):
    """Log OTA upload start."""
    get_logger().log(EventSource.USER, "OTA_START", {
        "target_ip": target_ip
    })


def log_ota_end(success: bool, duration_s: float):
    """Log OTA upload completion."""
    get_logger().log(EventSource.USER, "OTA_END", {
        "success": success,
        "duration_s": duration_s
    })
