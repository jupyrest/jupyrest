from .entity import NotebookExecution, NotebookExecutionStatus
from typing import List

from ..error import InvalidExecutionState

def _assert_status(execution: NotebookExecution, expected_status: List[NotebookExecutionStatus]):
    if execution.status not in expected_status:
        raise InvalidExecutionState(
            execution_id=execution.execution_id,
            current_status=execution.status,
            expected_status=list(map(lambda s: s.value, expected_status)),
        )

