from ..contracts import DependencyBag, NotebookExecutionTaskHandler
from ..notebook_execution.commands import complete_execution

class DefaultNotebookExecutionTaskHandler(NotebookExecutionTaskHandler):

    async def submit_execution_task(self, execution_id: str, deps: DependencyBag):
        await complete_execution(execution_id=execution_id, deps=deps)