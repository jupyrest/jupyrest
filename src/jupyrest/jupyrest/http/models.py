from pydantic import BaseModel
from typing import Dict, Any, Optional, List


class NotebookExecutionRequest(BaseModel):
    parameters: Dict


class NotebookExecutionResponse(BaseModel):
    execution_id: str
    status: str
    notebook_id: str
    parameters: Dict[str, Any]
    artifacts: Dict[str, str]

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
