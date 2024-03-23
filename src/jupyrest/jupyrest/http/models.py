import datetime
from unittest.mock import Base
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from ..notebook_execution.entity import (
    NotebookExecutionStatus,
    NotebookExecutionCompletionStatus,
)


class NotebookExecutionRequest(BaseModel):
    parameters: Dict


class ExecutionCompletionDetails(BaseModel):
    completion_status: str
    end_time: str
    artifacts: Dict[str, str]


class NotebookExecutionResponse(BaseModel):
    execution_id: str
    status: NotebookExecutionStatus
    notebook_id: str
    parameters: Dict[str, Any]
    execution_accepted_ts: datetime.datetime
    execution_start_ts: Optional[datetime.datetime] = None
    execution_end_ts: Optional[datetime.datetime] = None
    execution_completion_status: Optional[NotebookExecutionCompletionStatus] = None
    has_output: Optional[bool] = None
    has_exception: Optional[bool] = None
    artifacts: Optional[Dict[str, str]] = None


class NotebookExecutionAsyncResponse(BaseModel):
    execution_id: str
    status: str
    notebook_id: str


class NotebookResponse(BaseModel):
    notebook_id: str
    input_schema: Dict
    output_schema: Dict


class NotebookList(BaseModel):
    notebooks: List[str]
