from enum import Enum

from pydantic import BaseModel


class EventKind(str, Enum):
    """
    Represents different kinds of events that can occur within the system.
    
        Class Attributes:
            ANALYZED: Indicates an event where something was analyzed.
            CREATED: Indicates an event where something was created.
            GENERATED: Indicates an event where something was generated.
            SET: Indicates an event where something was set.
            REFINED: Indicates an event where something was refined.
            UPDATED: Indicates an event where something was updated.
            MOVED: Indicates an event where something was moved.
            WRITTEN: Indicates an event where something was written.
            EXISTS: Indicates an event where something was found to exist.
            UPLOADED: Indicates an event where something was uploaded.
            SKIPPED: Indicates an event where something was skipped.
            FAILED: Indicates an event where something failed.
    """

    ANALYZED = "analyzed"
    CREATED = "created"
    GENERATED = "generated"
    SET = "set"
    REFINED = "refined"
    UPDATED = "updated"
    MOVED = "moved"
    WRITTEN = "written"
    EXISTS = "exists"
    UPLOADED = "uploaded"
    SKIPPED = "skipped"
    FAILED = "failed"


class OperationEvent(BaseModel):
    """
    Represents an event that occurs during an operation, capturing relevant details such as the event type, target, and associated data.
    
        Class Attributes:
        - kind: The type of event (e.g., 'start', 'complete', 'error').
        - target: The object or entity that the event pertains to.
        - data: Additional information or payload associated with the event.
    """

    kind: EventKind
    target: str
    data: dict = {}
