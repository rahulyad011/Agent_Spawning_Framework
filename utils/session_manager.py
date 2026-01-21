from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime_agents.shared.llm import Message


@dataclass
class FileMetadata:
    """Metadata for uploaded files."""

    filename: str
    file_path: str
    file_type: str
    size_bytes: int
    uploaded_at: str


@dataclass
class ImageMetadata:
    """Metadata for uploaded images."""

    filename: str
    file_path: str
    image_format: str
    size_bytes: int
    uploaded_at: str


@dataclass
class DBConnection:
    """Database connection information."""

    connection_id: str
    db_type: str  # postgresql, mysql, sqlite
    connection_string: str  # May be masked in UI
    selected_tables: List[str] = field(default_factory=list)
    connected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Session:
    """Session data structure for chat sessions."""

    session_id: str
    created_at: str
    last_accessed: str
    chat_history: List[Dict[str, str]] = field(default_factory=list)
    files: List[FileMetadata] = field(default_factory=list)
    images: List[ImageMetadata] = field(default_factory=list)
    db_connections: List[DBConnection] = field(default_factory=list)
    agent_state: Dict[str, Any] = field(default_factory=dict)
    agent_results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert FileMetadata and ImageMetadata to dicts
        data["files"] = [asdict(f) for f in self.files]
        data["images"] = [asdict(i) for i in self.images]
        data["db_connections"] = [asdict(db) for db in self.db_connections]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Session:
        """Create Session from dictionary."""
        # Convert nested dicts back to objects
        files = [FileMetadata(**f) for f in data.get("files", [])]
        images = [ImageMetadata(**i) for i in data.get("images", [])]
        db_connections = [DBConnection(**db) for db in data.get("db_connections", [])]

        return cls(
            session_id=data["session_id"],
            created_at=data["created_at"],
            last_accessed=data["last_accessed"],
            chat_history=data.get("chat_history", []),
            files=files,
            images=images,
            db_connections=db_connections,
            agent_state=data.get("agent_state", {}),
            agent_results=data.get("agent_results", []),
        )

    def add_message(self, role: str, content: str) -> None:
        """Add a message to chat history."""
        self.chat_history.append({"role": role, "content": content})
        self.last_accessed = datetime.utcnow().isoformat()

    def get_messages(self) -> List[Message]:
        """Get chat history as Message objects."""
        return [
            Message(role=m["role"], content=m["content"]) for m in self.chat_history
        ]


class SessionManager:
    """Manages session storage and retrieval."""

    def __init__(self, sessions_dir: str = "sessions", uploads_dir: str = "uploads"):
        self.sessions_dir = Path(sessions_dir)
        self.uploads_dir = Path(uploads_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.uploads_dir.mkdir(exist_ok=True)

    def create_session(self, session_id: Optional[str] = None) -> Session:
        """Create a new session."""
        if session_id is None:
            session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"

        session = Session(
            session_id=session_id,
            created_at=datetime.utcnow().isoformat(),
            last_accessed=datetime.utcnow().isoformat(),
        )

        self.save_session(session)
        return session

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session from file."""
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return None

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Session.from_dict(data)
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    def save_session(self, session: Session) -> None:
        """Save a session to file."""
        session.last_accessed = datetime.utcnow().isoformat()
        session_file = self.sessions_dir / f"{session.session_id}.json"

        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving session {session.session_id}: {e}")

    def list_sessions(self) -> List[str]:
        """List all session IDs."""
        if not self.sessions_dir.exists():
            return []

        sessions = []
        for file in self.sessions_dir.glob("*.json"):
            session_id = file.stem
            sessions.append(session_id)

        return sorted(sessions, reverse=True)  # Most recent first

    def delete_session(self, session_id: str) -> None:
        """Delete a session and its associated files."""
        # Delete session file
        session_file = self.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

        # Delete uploads directory
        uploads_path = self.uploads_dir / session_id
        if uploads_path.exists():
            import shutil

            shutil.rmtree(uploads_path)

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """Delete sessions older than specified days. Returns count of deleted sessions."""
        cutoff = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
        deleted = 0

        for session_id in self.list_sessions():
            session = self.load_session(session_id)
            if session:
                try:
                    last_accessed = datetime.fromisoformat(session.last_accessed).timestamp()
                    if last_accessed < cutoff:
                        self.delete_session(session_id)
                        deleted += 1
                except Exception:
                    pass

        return deleted

    def get_session_uploads_dir(self, session_id: str) -> Path:
        """Get the uploads directory for a session."""
        uploads_path = self.uploads_dir / session_id
        uploads_path.mkdir(parents=True, exist_ok=True)
        (uploads_path / "files").mkdir(exist_ok=True)
        (uploads_path / "images").mkdir(exist_ok=True)
        return uploads_path
