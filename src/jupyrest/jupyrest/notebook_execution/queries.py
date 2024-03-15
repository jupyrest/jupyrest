from .entity import NotebookExecution
from ..contracts import DependencyBag

async def get_execution(execution_id: str, deps: DependencyBag) -> NotebookExecution:
    execution_repository = deps.notebook_execution_repository
    execution = await execution_repository.get(
        execution_id=execution_id
    )
    return execution

async def get_execution_artifact(execution_id: str, deps: DependencyBag):
    execution = await get_execution(execution_id=execution_id, deps=deps)
    