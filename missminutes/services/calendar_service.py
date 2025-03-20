import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime
from pathlib import Path
import zoneinfo
import tzlocal
from google.auth.exceptions import RefreshError
from ..config import config


class CalendarService:
    """Handles Google Calendar integration"""

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    TOKEN_FILE = "token.pickle"
    CREDENTIALS_FILE = "credentials.json"

    def __init__(self):
        self.creds = None
        self.service = None
        self.timezone = str(tzlocal.get_localzone())
        if config.use_google_calendar:
            self._authenticate()

    def _authenticate(self):
        """Handle Google Calendar authentication with better error handling"""
        config_dir = Path.home() / ".config" / "missminutes"
        config_dir.mkdir(parents=True, exist_ok=True)
        token_path = config_dir / self.TOKEN_FILE
        creds_path = config_dir / self.CREDENTIALS_FILE

        try:
            if token_path.exists():
                with open(token_path, "rb") as token:
                    self.creds = pickle.load(token)

            # If credentials are invalid or expired
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    try:
                        self.creds.refresh(Request())
                    except RefreshError:
                        # If refresh fails, remove token and start fresh
                        token_path.unlink(missing_ok=True)
                        self.creds = None

                # If no valid credentials available, start fresh OAuth flow
                if not self.creds:
                    if not creds_path.exists():
                        raise FileNotFoundError(
                            f"Please place your Google Calendar credentials.json file in {creds_path}"
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(creds_path), self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)

                # Save the new/refreshed credentials
                with open(token_path, "wb") as token:
                    pickle.dump(self.creds, token)

            self.service = build("calendar", "v3", credentials=self.creds)

        except Exception as e:
            print(f"Failed to authenticate with Google Calendar: {e}")
            print("You may need to delete ~/.config/missminutes/token.pickle and try again")
            # Initialize service as None to allow graceful degradation
            self.service = None

    def _ensure_authenticated(self):
        """Ensure we have a working service, attempt reauth if needed"""
        if not config.use_google_calendar:
            return
        if not self.service:
            self._authenticate()
        if not self.service:
            raise RuntimeError("Could not authenticate with Google Calendar")

    def create_event(self, task, scheduled_time):
        """Create a calendar event for a scheduled task"""
        if not config.use_google_calendar:
            return None
        try:
            self._ensure_authenticated()
            
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

            event = (
                self.service.events().insert(calendarId="primary", body=event).execute()
            )
            return event["id"]
        except Exception as e:
            print(f"Failed to create calendar event: {e}")
            return None

    def update_event(self, event_id, task, scheduled_time):
        """Update an existing calendar event for a scheduled task"""
        if not config.use_google_calendar:
            return False
        try:
            self._ensure_authenticated()
            
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

            self.service.events().update(
                calendarId="primary", eventId=event_id, body=event
            ).execute()
            return True
        except Exception as e:
            print(f"Failed to update calendar event: {e}")
            return False

    def delete_event(self, event_id):
        """Delete a calendar event"""
        if not config.use_google_calendar:
            return False
        try:
            self._ensure_authenticated()
            
            self.service.events().delete(
                calendarId="primary", eventId=event_id
            ).execute()
            return True
        except Exception as e:
            print(f"Failed to delete calendar event: {e}")
            return False

    def get_all_events(self):
        """Get all events created by missminutes"""
        if not config.use_google_calendar:
            return []
        try:
            self._ensure_authenticated()
            
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
