from abc import ABC, abstractmethod
from pydantic import BaseModel
from fastapi.exceptions import HTTPException

from .nbschema import SchemaValidationResponse


class BaseError(BaseModel, ABC):
    ...


class HTTPError(ABC):
    @abstractmethod
    def to_http_exception(self) -> HTTPException:
        ...


class InternalError(HTTPError, BaseError):
    details: str

    def to_http_exception(self) -> HTTPException:
        raise


class BadInput(BaseError):
    details: str


class PluginNotFound(BaseError):
    plugin_name: str


class NotebookNotFound(BaseError):
    notebook_id: str


class InputSchemaValidationError(BaseError):
    validation: SchemaValidationResponse
