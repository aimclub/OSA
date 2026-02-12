from enum import Enum

from pydantic import BaseModel


class EventKind(str, Enum):
    GENERATED = "generated"
    REFINED = "refined"
    WRITTEN = "written"
    EXISTS = "exists"
    UPDATED = "updated"
    SET = "set"
    SKIPPED = "skipped"
    FAILED = "failed"


class OperationEvent(BaseModel):
    kind: EventKind
    target: str
    data: dict = {}
