from enum import Enum

from pydantic import BaseModel


class EventKind(str, Enum):
    ANALYZED = "analyzed"
    CREATED = "created"
    GENERATED = "generated"
    SET = "set"
    REFINED = "refined"
    UPDATED = "updated"
    MOVED = "moved"
    WRITTEN = "written"
    EXISTS = "exists"
    SKIPPED = "skipped"
    FAILED = "failed"


class OperationEvent(BaseModel):
    kind: EventKind
    target: str
    data: dict = {}
