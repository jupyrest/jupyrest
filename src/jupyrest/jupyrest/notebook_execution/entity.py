from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
from ..file_object import FileObject
from ..model import NamedModel


class NotebookExecutionStatus(str, Enum):
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
    ipynb: FileObject
    html_report: FileObject
    html: FileObject
    exception: Optional[FileObject]
    output: Optional[FileObject]

    class Config:
        __ns__ = "jupyrest.notebook_execution.entity.NotebookExecutionCompletionDetails"


class NotebookExecution(NamedModel):
    execution_id: str
    notebook_id: str
    parameters: Dict[str, Any]
    status: NotebookExecutionStatus
    accepted_time: datetime
    start_time: Optional[datetime]
    completion_details: Optional[NotebookExecutionCompletionDetails] = None

    class Config:
        __ns__ = "jupyrest.notebook_execution.entity.NotebookExecution"