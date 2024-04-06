import json
from typing import List, Dict, Optional
from abc import ABC

class BaseError(Exception, ABC):
    def __init__(self, code: str, message: str, data: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.data = data or {}
        super().__init__(self.to_json())

    def to_json(self) -> str:
        return json.dumps(self.dict())

    def dict(self):
        return {"code": self.code, "message": self.message, "data": self.data}


class InternalError(BaseError):
    def __init__(self):
        super().__init__(code="INTERNAL_ERROR", message="An internal error occurred.")


class InvalidInputSchema(BaseError):
    def __init__(self, schema_error: str):
        self.schema_error = schema_error
        super().__init__(
            code="INVALID_INPUT_SCHEMA",
            message=f"The input parameters do not match the schema for the notebook. Details: {self.schema_error}",
        )


class InvalidExecutionState(BaseError):
    def __init__(
        self, execution_id: str, current_status: str, expected_status: List[str]
    ):
        super().__init__(
            code="INVALID_EXECUTION_STATE",
            message=f"The notebook execution is not in a valid state to perform this action. Current status: {current_status}. Expected status: {expected_status}",
        )
        self.execution_id = execution_id
        self.current_status = current_status
        self.expected_status = expected_status


class NotebookExecutionNotFound(BaseError):
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        super().__init__(
            code="NOTEBOOK_EXECUTION_NOT_FOUND",
            message=f"Notebook execution {self.execution_id} not found.",
        )


class NotebookNotFound(BaseError):
    def __init__(self, notebook_id: str):
        self.notebook_id = notebook_id
        super().__init__(
            code="NOTEBOOK_NOT_FOUND", message=f"Notebook {self.notebook_id} not found."
        )

class NotebookExecutionArtifactNotFound(BaseError):
    def __init__(self, artifact_name: str):
        super().__init__(
            code="NOTEBOOK_EXECUTION_ARTIFACT_NOT_FOUND",
            message=f"Notebook execution artifact {artifact_name} not found.",
        )

class FileObjectNotFound(BaseError):
    def __init__(self, path: str):
        self.path = path
        super().__init__(
            code="FILE_OBJECT_NOT_FOUND",
            message=f"File object {self.path} not found.",
        )

class UnrecognizedFileObjectScheme(BaseError):
    def __init__(self, scheme: str):
        super().__init__(
            code="UNRECOGNIZED_FILE_OBJECT_SCHEME",
            message=f"Unrecognized scheme: {scheme}",
        )