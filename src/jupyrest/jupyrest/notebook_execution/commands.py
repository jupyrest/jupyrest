from typing import Any, Dict, List
from uuid import uuid4
from datetime import datetime
import json
from .entity import NotebookExecution, NotebookExecutionStatus, NotebookExecutionCompletionStatus, NotebookExecutionCompletionDetails
from ..contracts import DependencyBag
from ..errors2 import InvalidInputSchema, InvalidExecutionState
import logging
import asyncio

logger = logging.getLogger(__name__)

def _assert_status(execution: NotebookExecution, expected_status: List[NotebookExecutionStatus]):
    if execution.status not in expected_status:
        raise InvalidExecutionState(
            execution_id=execution.execution_id,
            current_status=execution.status,
            expected_status=list(map(lambda s: s.value, expected_status)),
        )

def create(notebook_id: str, parameters: Dict[str, Any]) -> NotebookExecution:
    return NotebookExecution(
        execution_id=str(uuid4()),
        notebook_id=notebook_id,
        parameters=parameters,
        status=NotebookExecutionStatus.INVALID,
        start_time=None,
        completion_details=None,
    )


async def accept(execution: NotebookExecution, deps: DependencyBag):
    _assert_status(execution=execution, expected_status=[NotebookExecutionStatus.INVALID])
    notebook_config = await deps.notebook_repository.get(notebook_id=execution.notebook_id)
    input_validation = deps.notebook_input_output_validator.validate_input(
        notebook_config=notebook_config,
        parameters=execution.parameters
    )
    if input_validation.is_valid:
        execution.status = NotebookExecutionStatus.ACCEPTED
    else:
        schema_error = input_validation.error or ""
        raise InvalidInputSchema(schema_error=schema_error)
    await deps.notebook_execution_repository.save(execution=execution)


async def begin_execution(
    execution: NotebookExecution,
    deps: DependencyBag,
):
    _assert_status(execution=execution, expected_status=[NotebookExecutionStatus.ACCEPTED])
    execution.status = NotebookExecutionStatus.EXECUTING
    execution.start_time = datetime.utcnow()
    await deps.notebook_execution_repository.save(execution=execution)
    await deps.notebook_execution_task_handler.submit_execution_task(
        execution_id=execution.execution_id,
        deps=deps
    )


async def complete_execution(
    execution: NotebookExecution,
    deps: DependencyBag,
):
    _assert_status(execution=execution, expected_status=[NotebookExecutionStatus.EXECUTING])
    notebook_config = await deps.notebook_repository.get(
        notebook_id=execution.notebook_id
    )
    executor = deps.notebook_executor
    notebook = deps.notebook_parameterizier.parameterize_notebook(
        notebook_config=notebook_config,
        parameters=execution.parameters
    )
    try:
        exception = await executor.execute_notebook_async(
            notebook=notebook
        )
    except Exception as e:
        logger.exception(f"Execution error {execution.execution_id}")
        execution.status = NotebookExecutionStatus.INTERNAL_ERROR
    else:
        end_time = datetime.utcnow()
        execution.status = NotebookExecutionStatus.COMPLETED
        if exception is not None:
            completion_status = NotebookExecutionCompletionStatus.FAILED
        else:
            completion_status = NotebookExecutionCompletionStatus.SUCCEEDED
        output_result = deps.notebook_output_reader.get_output(notebook=notebook)
        ipynb_path = deps.notebook_execution_file_namer.get_ipynb_name(execution=execution)
        html_report_path = deps.notebook_execution_file_namer.get_html_report_name(execution=execution)
        html_path = deps.notebook_execution_file_namer.get_html_name(execution=execution)
        ipynb, html_report, html = await asyncio.gather(
            deps.file_obj.create(ipynb_path, deps.notebook_converter.convert_notebook_to_str(notebook=notebook)),
            deps.file_obj.create(html_report_path, deps.notebook_converter.convert_notebook_to_html(notebook=notebook, report_mode=True)),
            deps.file_obj.create(html_path, deps.notebook_converter.convert_notebook_to_html(notebook=notebook, report_mode=False))
        )
        execution.completion_details = NotebookExecutionCompletionDetails(
            completion_status=completion_status,
            end_time=end_time,
            output_result=output_result,
            exception=exception,
            ipynb=ipynb,
            html_report_path=html_report,
            html_path=html
        )
    finally:
        await deps.notebook_execution_repository.save(execution=execution)