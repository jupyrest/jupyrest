from enum import Enum
from typing import Union
from .entity import NotebookExecution, NotebookExecutionStatus
from ..contracts import DependencyBag
from .common import _assert_status
from ..errors2 import NotebookExecutionArtifactNotFound

async def get_execution(execution_id: str, deps: DependencyBag) -> NotebookExecution:
    execution_repository = deps.notebook_execution_repository
    execution = await execution_repository.get(
        execution_id=execution_id
    )
    return execution

class ExecutionArtifactType(str, Enum):
    HTML = "html"
    IPYNB = "ipynb"
    HTML_REPORT = "html_report"

async def get_execution_artifact(execution_id: Union[str, NotebookExecution], deps: DependencyBag, artifact_type: ExecutionArtifactType) -> str:
    if isinstance(execution_id, str):
        execution = await get_execution(execution_id=execution_id, deps=deps)
    _assert_status(execution=execution, expected_status=[NotebookExecutionStatus.COMPLETED])
    completion_details = execution.completion_details
    assert completion_details is not None
    if artifact_type == ExecutionArtifactType.HTML:
        file_obj = completion_details.html
    elif artifact_type == ExecutionArtifactType.IPYNB:
        file_obj = completion_details.ipynb
    elif artifact_type == ExecutionArtifactType.HTML_REPORT:
        file_obj = completion_details.html_report
    else:
        raise NotebookExecutionArtifactNotFound(artifact_name=artifact_type)
    
    return await deps.file_obj_client.get_content(file_object=file_obj)

    