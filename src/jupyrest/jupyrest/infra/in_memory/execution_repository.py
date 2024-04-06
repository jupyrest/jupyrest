from typing import Dict

from ...contracts import NotebookExecutionRepository
from ...notebook_execution.entity import NotebookExecution
from ...error import NotebookExecutionNotFound

class InMemoryNotebookExecutionRepository(NotebookExecutionRepository):
    def __init__(self) -> None:
        self._executions: Dict[str, str] = {}

    async def get(self, execution_id: str) -> NotebookExecution:
        try:
            return NotebookExecution.parse_raw(self._executions[execution_id])
        except KeyError:
            raise NotebookExecutionNotFound(execution_id=execution_id)

    async def save(self, execution: NotebookExecution) -> None:
        self._executions[execution.execution_id] = execution.json()

    async def create(self, execution: NotebookExecution) -> None:
        self._executions[execution.execution_id] = execution.json()