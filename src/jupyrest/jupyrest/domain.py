import logging
from jupyrest.nbschema import SchemaValidationResponse
from typing import Any, Dict, Tuple, Iterable, Iterator, Optional, Type, Union
from nbformat.notebooknode import NotebookNode
from pydantic import BaseModel
from datetime import datetime
import json
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseEvent(BaseModel):
    pass


class NotebookExecutionCreated(BaseEvent):
    notebook_id: str
    plugin_name: str
    parameters: Dict


class NotebookExecuted(BaseEvent):
    start_time: datetime
    end_time: datetime
    output_validation: SchemaValidationResponse
    exception: Optional[str] = None
    output_json_str: Optional[str] = None


class EventsDirectory:
    def __init__(self) -> None:
        self._id_to_event_type: Dict[str, Type[BaseEvent]] = {}
        self._event_type_to_id: Dict[Type[BaseEvent], str] = {}

    @classmethod
    def from_tuples(cls, event_types: Iterable[Tuple[str, Type[BaseEvent]]]):
        directory = cls()
        for event_id, event_type in event_types:
            directory.put(event_id=event_id, event_type=event_type)
        return directory

    def put(self, event_id: str, event_type: Type[BaseEvent]):
        if event_id in self._id_to_event_type:
            raise Exception(
                f"Event {self._id_to_event_type[event_id]} with id {event_id} already exists."
            )
        self._id_to_event_type[event_id] = event_type
        self._event_type_to_id[event_type] = event_id

    def get_event_type(self, event_id: str) -> Type[BaseEvent]:
        return self._id_to_event_type[event_id]

    def get_event_id(self, event_type: Type[BaseEvent]) -> str:
        return self._event_type_to_id[event_type]


class BaseEventStore(ABC):
    @abstractmethod
    def save_event(self, event: BaseEvent, key: Any):
        """Save an event to this event store using a key.

        Args:
            event (BaseEvent): event to save
        """
        pass

    @abstractmethod
    def get_event(self, key: Any) -> Optional[BaseEvent]:
        """Get a saved event under a key. If not exists, return None.

        Args:
            key (Any):

        Returns:
            Optional[BaseEvent]:
        """
        pass


class NotebookEventStore(BaseEventStore):

    directory = EventsDirectory.from_tuples(
        [
            ("notebook_execution_created", NotebookExecutionCreated),
            ("notebook_executed", NotebookExecuted),
        ]
    )

    event_id_key = "__event_id"

    def __init__(self, notebook: NotebookNode) -> None:
        self.notebook = notebook
        if "metadata" not in self.notebook:
            self.notebook["metadata"] = {}
        if "jupyrest" not in self.notebook["metadata"]:
            self.notebook["metadata"]["jupyrest"] = {}
        if "events" not in self.notebook["metadata"]["jupyrest"]:
            self.notebook["metadata"]["jupyrest"]["events"] = {}

    def save_event(self, event: BaseEvent, key=None):
        """Save an event in a notebook. Here the key is ignored and
        we use this class's EventsDirectory to generate a key for a given
        BaseEvent type.

        Args:
            event (BaseEvent):
            key ([type], optional): ignored
        """
        # convert event to json
        event_data = json.loads(event.json())
        # add event type info (if specified)
        event_id = self.directory.get_event_id(event_type=type(event))
        event_data[self.event_id_key] = event_id
        # save in notebook object
        self.notebook["metadata"]["jupyrest"]["events"][event_id] = event_data

    def get_event(self, key: Type[BaseEvent]) -> Optional[BaseEvent]:
        events = dict(self.notebook["metadata"]["jupyrest"]["events"])
        event_id = self.directory.get_event_id(event_type=key)
        event_json = events.get(event_id, None)
        if event_json is not None:
            return key.parse_obj(event_json)
        else:
            return None
