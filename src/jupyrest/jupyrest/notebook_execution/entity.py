from typing import Dict, Any, Optional, Protocol
from enum import Enum
from datetime import datetime
from ..file_io.core import FileObject
from ..model import NamedModel
from ..nbschema import OutputResult


class NotebookExecutionStatus(str, Enum):
    INVALID = "INVALID"
    ACCEPTED = "ACCEPTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class NotebookExecutionCompletionStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"

class NotebookExecutionCompletionDetails(NamedModel):
    completion_status: NotebookExecutionCompletionStatus
    end_time: datetime
    output_result: OutputResult
    exception: Optional[str]
    ipynb: FileObject 
    html_report: FileObject
    html: FileObject

    class Config:
        __ns__ = "jupyrest.notebook_execution.entity.NotebookExecutionCompletionDetails"

class NotebookExecution(NamedModel):
    execution_id: str
    notebook_id: str
    parameters: Dict[str, Any]
    status: str
    start_time: Optional[datetime]

    completion_details: Optional[NotebookExecutionCompletionDetails] = None

    class Config:
        __ns__ = "jupyrest.notebook_execution.entity.NotebookExecution"