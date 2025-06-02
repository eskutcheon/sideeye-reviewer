
import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

# lives in the `controllers` submodule, so it can be used/passed directly by the main app controller rather than handled by the data manager


@dataclass
class SessionLogEntry:
    timestamp: str
    item_id: str | None
    action: str                # "label", "undo", "start", "stop", …
    payload: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """ Tracks review metadata & writes per-session JSON log files """
    def __init__(self, reviewer_name: Optional[str] = None, log_dir: Optional[str] = "sessions"):
        self.dir = Path(log_dir)
        self.dir.mkdir(exist_ok=True, parents=True)
        #self.session_id = str(uuid.uuid4().hex[:8])
        self.session_id = os.getenv("REVIEW_SESSION", str(uuid.uuid4().hex[:8])) #datetime.now().strftime("%Y%m%dT%H%M%S"))
        self.reviewer = reviewer_name or os.getenv("USER", os.getenv("USERNAME", "anonymous"))
        self._entries: List[SessionLogEntry] = []
        self.record(action="start", item_id=None)

    def record(self, action: str, item_id: Optional[str], **payload):
        self._entries.append(SessionLogEntry(
            timestamp=datetime.now(tz=timezone.utc).isoformat(), #+ "Z",
            item_id=item_id,
            action=action,
            payload=payload,
        ))

    def flush(self):
        out = self.dir / f"session_{self.session_id}.json"
        json.dump({
            "reviewer": self.reviewer,
            "session_id": self.session_id,
            "entries": [asdict(e) for e in self._entries]
        }, out.open("w"), indent=2)

    def get_last_index(self) -> int:
        """ returns an index one greater than the last entry in the session log """
        last_idx = 0
        for e in self._entries:
            if e.action == "label":
                last_idx += 1
            elif e.action == "undo":
                last_idx -= 1
        return max(0, last_idx)


    @staticmethod
    def resume_session(session_file: str) -> 'SessionManager':
        """ Loads a session from a JSON file and returns a SessionManager instance """
        if not os.path.exists(session_file):
            raise FileNotFoundError(f"Session file '{session_file}' does not exist.")
        log_dir = os.path.dirname(session_file)
        with open(session_file, "r") as f:
            data = dict(json.load(f))
        sm = SessionManager(reviewer_name=data.get("reviewer", "anonymous"), log_dir=log_dir)
        sm.session_id = data.get("session_id", str(uuid.uuid4().hex[:8]))
        sm._entries = [SessionLogEntry(**entry) for entry in data.get("entries", [])]
        sm.record(action="resume", item_id=None)
        return sm