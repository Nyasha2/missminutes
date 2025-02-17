import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime
from pathlib import Path
import zoneinfo
import tzlocal


class CalendarService:
    """Handles Google Calendar integration"""

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    TOKEN_FILE = "token.pickle"
    CREDENTIALS_FILE = "credentials.json"

    def __init__(self):
        self.creds = None
        self.service = None
        self.timezone = str(tzlocal.get_localzone())
        self._authenticate()

    def _authenticate(self):
        """Handle Google Calendar authentication"""
        # Look for token in config directory
        config_dir = Path.home() / ".config" / "missminutes"
        config_dir.mkdir(parents=True, exist_ok=True)
        token_path = config_dir / self.TOKEN_FILE
        creds_path = config_dir / self.CREDENTIALS_FILE

        if token_path.exists():
            with open(token_path, "rb") as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not creds_path.exists():
                    raise FileNotFoundError(
                        f"Please place your Google Calendar credentials.json file in {creds_path}"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_path), self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            with open(token_path, "wb") as token:
                pickle.dump(self.creds, token)

        self.service = build("calendar", "v3", credentials=self.creds)

    def create_event(self, task, scheduled_time):
        """Create a calendar event for a scheduled task"""
        event = {
            "summary": task.title,
            "description": f"Task ID: {task.id}\nDuration: {task.duration}",
            "start": {
                "dateTime": scheduled_time.isoformat(),
                "timeZone": self.timezone,
            },
            "end": {
                "dateTime": (scheduled_time + task.duration).isoformat(),
                "timeZone": self.timezone,
            },
            "extendedProperties": {
                "private": {"task_id": str(task.id), "missminutes_task": "true"}
            },
        }

        try:
            event = (
                self.service.events().insert(calendarId="primary", body=event).execute()
            )
            return event["id"]
        except Exception as e:
            print(f"Failed to create calendar event: {e}")
            return None

    def update_event(self, event_id, task, scheduled_time):
        """Update an existing calendar event for a scheduled task"""
        event = {
            "summary": task.title,
            "description": f"Task ID: {task.id}\nDuration: {task.duration}",
            "start": {
                "dateTime": scheduled_time.isoformat(),
                "timeZone": self.timezone,
            },
            "end": {
                "dateTime": (scheduled_time + task.duration).isoformat(),
                "timeZone": self.timezone,
            },
        }

        try:
            self.service.events().update(
                calendarId="primary", eventId=event_id, body=event
            ).execute()
            return True
        except Exception as e:
            print(f"Failed to update calendar event: {e}")
            return False

    def delete_event(self, event_id):
        """Delete a calendar event"""
        try:
            self.service.events().delete(
                calendarId="primary", eventId=event_id
            ).execute()
            return True
        except Exception as e:
            print(f"Failed to delete calendar event: {e}")
            return False

    def get_all_events(self):
        """Get all events created by missminutes"""
        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    privateExtendedProperty="missminutes_task=true",
                )
                .execute()
            )
            return events_result.get("items", [])
        except Exception as e:
            print(f"Failed to fetch calendar events: {e}")
            return []
