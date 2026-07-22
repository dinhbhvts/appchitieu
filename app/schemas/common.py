"""Small shared schema pieces used by several endpoints."""

from pydantic import BaseModel


class Message(BaseModel):
    """A simple {"detail": "..."} response, e.g. for delete confirmations."""

    detail: str
