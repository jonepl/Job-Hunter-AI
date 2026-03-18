"""Resume domain entity."""

from datetime import datetime

from pydantic import BaseModel


class Resume(BaseModel):
    """Represents the parsed candidate resume."""

    raw_text: str
    parsed_at: datetime
