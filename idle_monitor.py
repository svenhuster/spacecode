"""
Idle monitoring system for SpacedCode auto-shutdown functionality.
"""

import os
import time
import threading
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional


class IdleMonitor:
    """Monitor application idle time and trigger shutdown when idle timeout is reached."""

    def __init__(self, timeout_minutes: int = 480, check_interval: int = 60):
        """
        Initialize idle monitor.

        Args:
            timeout_minutes: Minutes of inactivity before shutdown (default: 8 hours)
            check_interval: How often to check idle time in seconds (default: 60s)
        """
        self.timeout_minutes = timeout_minutes
        self.check_interval = check_interval
        self.last_activity = datetime.now()
        self.shutdown_callback: Optional[callable] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.running = False
        self._lock = threading.Lock()

        # Only enable auto-shutdown if we're running with socket activation
        self.socket_activation = os.environ.get('SPACEDCODE_SOCKET_ACTIVATION', 'false').lower() == 'true'

        if self.socket_activation:
            print(f"🕐 Idle monitor enabled: auto-shutdown after {timeout_minutes} minutes of inactivity")
        else:
            print("🕐 Idle monitor disabled: not running with socket activation")

    def record_activity(self):
        """Record that activity has occurred."""
        if not self.socket_activation:
            return

        with self._lock:
            self.last_activity = datetime.now()

    def get_idle_time_minutes(self) -> float:
        """Get current idle time in minutes."""
        with self._lock:
            idle_time = datetime.now() - self.last_activity
            return idle_time.total_seconds() / 60

    def start_monitoring(self, shutdown_callback: callable):
        """Start the idle monitoring thread."""
        if not self.socket_activation:
            return

        self.shutdown_callback = shutdown_callback
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"🚀 Idle monitoring started (timeout: {self.timeout_minutes} minutes)")

    def stop_monitoring(self):
        """Stop the idle monitoring thread."""
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)

    def _monitor_loop(self):
        """Main monitoring loop (runs in separate thread)."""
        while self.running:
            try:
                idle_minutes = self.get_idle_time_minutes()

                if idle_minutes >= self.timeout_minutes:
                    print(f"⏰ Idle timeout reached ({idle_minutes:.1f} minutes). Triggering shutdown...")
                    if self.shutdown_callback:
                        self.shutdown_callback()
                    break
                else:
                    # Log periodic status (every hour)
                    if int(idle_minutes) % 60 == 0 and idle_minutes > 0:
                        remaining = self.timeout_minutes - idle_minutes
                        print(f"⏱️  Idle for {idle_minutes:.0f} minutes. Auto-shutdown in {remaining:.0f} minutes.")

                time.sleep(self.check_interval)

            except Exception as e:
                print(f"⚠️  Error in idle monitoring: {e}")
                time.sleep(self.check_interval)

    def get_status(self) -> dict:
        """Get current idle monitor status."""
        if not self.socket_activation:
            return {
                'enabled': False,
                'reason': 'Socket activation not enabled'
            }

        idle_minutes = self.get_idle_time_minutes()
        remaining_minutes = max(0, self.timeout_minutes - idle_minutes)

        return {
            'enabled': True,
            'timeout_minutes': self.timeout_minutes,
            'idle_minutes': round(idle_minutes, 1),
            'remaining_minutes': round(remaining_minutes, 1),
            'last_activity': self.last_activity.isoformat(),
            'will_shutdown_at': (self.last_activity + timedelta(minutes=self.timeout_minutes)).isoformat()
        }


class GracefulShutdown:
    """Handle graceful shutdown of the Flask application."""

    def __init__(self, app):
        self.app = app
        self.shutdown_requested = False

    def shutdown(self):
        """Initiate graceful shutdown."""
        if self.shutdown_requested:
            return

        self.shutdown_requested = True
        print("🛑 Graceful shutdown initiated...")

        try:
            # Create final database backup before shutdown
            from utils import get_data_directory
            import shutil
            from datetime import datetime

            data_dir = get_data_directory()
            db_path = os.path.join(data_dir, 'leetcode.db')

            if os.path.exists(db_path):
                backup_dir = os.path.join(data_dir, 'backups')
                os.makedirs(backup_dir, exist_ok=True)

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = os.path.join(backup_dir, f'leetcode_shutdown_{timestamp}.db')

                shutil.copy2(db_path, backup_path)
                print(f"💾 Final database backup created: {backup_path}")

        except Exception as e:
            print(f"⚠️  Warning: Could not create shutdown backup: {e}")

        # Send SIGTERM to self to trigger shutdown
        print("✅ Shutdown complete. Service will restart on next request.")
        os.kill(os.getpid(), signal.SIGTERM)


# Global idle monitor instance
idle_monitor: Optional[IdleMonitor] = None


def create_idle_monitor(timeout_minutes: Optional[int] = None) -> IdleMonitor:
    """Create and configure the global idle monitor."""
    global idle_monitor

    if timeout_minutes is None:
        timeout_minutes = int(os.environ.get('SPACEDCODE_IDLE_TIMEOUT', '480'))

    idle_monitor = IdleMonitor(timeout_minutes=timeout_minutes)
    return idle_monitor


def get_idle_monitor() -> Optional[IdleMonitor]:
    """Get the global idle monitor instance."""
    return idle_monitor


def record_activity():
    """Convenience function to record activity on the global monitor."""
    if idle_monitor:
        idle_monitor.record_activity()