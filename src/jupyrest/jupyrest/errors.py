from pydantic import BaseModel
from .nbschema import SchemaValidationResponse


class BaseError(BaseModel):
    pass


class InternalError(BaseError):
    details: str


class BadInput(BaseError):
    details: str


class PluginNotFound(BaseError):
    plugin_name: str


class NotebookNotFound(BaseError):
    notebook_id: str


class InputSchemaValidationError(BaseError):
    validation: SchemaValidationResponse
