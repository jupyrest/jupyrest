from typing import Any, Dict, List
from uuid import uuid4
from datetime import datetime
import json
from .entity import (
    NotebookExecution,
    NotebookExecutionStatus,
    NotebookExecutionCompletionStatus,
    NotebookExecutionCompletionDetails,
)
from ..contracts import DependencyBag
from ..error import InvalidInputSchema
from .common import _assert_status
import logging
import asyncio

logger = logging.getLogger(__name__)


async def accept(
    notebook_id: str, parameters: Dict[str, Any], deps: DependencyBag
) -> NotebookExecution:
    notebook_config = await deps.notebook_repository.get(notebook_id=notebook_id)
    input_validation = deps.notebook_input_output_validator.validate_input(
        notebook_config=notebook_config, parameters=parameters
    )
    if input_validation.is_valid:
        execution = NotebookExecution(
            execution_id=str(uuid4()),
            notebook_id=notebook_id,
            parameters=parameters,
            status=NotebookExecutionStatus.ACCEPTED,
            accepted_time=datetime.utcnow(),
            start_time=None,
            completion_details=None,
        )
    else:
        schema_error = input_validation.error or ""
        raise InvalidInputSchema(schema_error=schema_error)
    await deps.notebook_execution_repository.save(execution=execution)
    return execution


async def begin_execution(
    execution: NotebookExecution,
    deps: DependencyBag,
):
    _assert_status(
        execution=execution, expected_status=[NotebookExecutionStatus.ACCEPTED]
    )
    await deps.notebook_execution_task_handler.submit_execution_task(
        execution_id=execution.execution_id, deps=deps
    )


async def complete_execution(
    execution_id: str,
    deps: DependencyBag,
):
    execution = await deps.notebook_execution_repository.get(execution_id)
    execution.status = NotebookExecutionStatus.EXECUTING
    execution.start_time = datetime.utcnow()
    await deps.notebook_execution_repository.save(execution=execution)
    _assert_status(
        execution=execution, expected_status=[NotebookExecutionStatus.EXECUTING]
    )
    notebook_config = await deps.notebook_repository.get(
        notebook_id=execution.notebook_id
    )
    executor = deps.notebook_executor
    notebook = deps.notebook_parameterizier.parameterize_notebook(
        notebook_config=notebook_config, parameters=execution.parameters
    )
    try:
        exception = await executor.execute_notebook_async(notebook=notebook)
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

        ipynb_path = deps.notebook_execution_file_namer.get_ipynb_name(
            execution=execution
        )
        html_report_path = deps.notebook_execution_file_namer.get_html_report_name(
            execution=execution
        )
        html_path = deps.notebook_execution_file_namer.get_html_name(
            execution=execution
        )

        ipynb = deps.file_obj_client.new_file_object(path=ipynb_path)
        html_report = deps.file_obj_client.new_file_object(path=html_report_path)
        html = deps.file_obj_client.new_file_object(path=html_path)
        exception_file = None
        output_file = None
        if output_result.present:
            output_path = deps.notebook_execution_file_namer.get_output_name(
                execution=execution
            )
            output_file = deps.file_obj_client.new_file_object(path=output_path)
            await deps.file_obj_client.set_content(
                output_file, output_result.json_str
            )

        if exception is not None:
            exception_path = deps.notebook_execution_file_namer.get_exception_name(
                execution=execution
            )
            exception_file = deps.file_obj_client.new_file_object(path=exception_path)
            await deps.file_obj_client.set_content(exception_file, exception)

        await asyncio.gather(
            deps.file_obj_client.set_content(
                ipynb,
                deps.notebook_converter.convert_notebook_to_str(notebook=notebook),
            ),
            deps.file_obj_client.set_content(
                html_report,
                deps.notebook_converter.convert_notebook_to_html(
                    notebook=notebook, report_mode=True
                ),
            ),
            deps.file_obj_client.set_content(
                html,
                deps.notebook_converter.convert_notebook_to_html(
                    notebook=notebook, report_mode=False
                ),
            ),
        )

        execution.completion_details = NotebookExecutionCompletionDetails(
            completion_status=completion_status,
            end_time=end_time,
            output=output_file,
            exception=exception_file,
            ipynb=ipynb,
            html_report=html_report,
            html=html,
        )
    finally:
        await deps.notebook_execution_repository.save(execution=execution)
