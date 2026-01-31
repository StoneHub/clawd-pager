"""
Clawd Pager Development Tools

Tools for improving the iteration loop when developing for the M5StickC Plus pager.

Components:
- EventLogger: SQLite-based event persistence
- SessionManager: Recording and replay of development sessions
- DashboardServer: WebSocket server for real-time monitoring
"""

from .event_logger import (
    EventLogger, EventSource, PagerEvent, get_logger,
    log_button_press, log_button_release, log_mode_change,
    log_display_update, log_api_call, log_audio_start, log_audio_end,
    log_stt_result, log_build_start, log_build_end, log_ota_start, log_ota_end
)
from .session_manager import SessionManager, SessionRecording, get_session_manager

__all__ = [
    # Event Logger
    'EventLogger', 'EventSource', 'PagerEvent', 'get_logger',
    'log_button_press', 'log_button_release', 'log_mode_change',
    'log_display_update', 'log_api_call', 'log_audio_start', 'log_audio_end',
    'log_stt_result', 'log_build_start', 'log_build_end', 'log_ota_start', 'log_ota_end',
    # Session Manager
    'SessionManager', 'SessionRecording', 'get_session_manager',
]
