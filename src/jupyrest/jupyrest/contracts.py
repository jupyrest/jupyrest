from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, AsyncIterable, Optional
from dataclasses import dataclass
from .nbschema import SchemaValidationResponse, OutputResult
from .notebook_config import NotebookConfig
from nbformat.notebooknode import NotebookNode
from .notebook_execution.entity import NotebookExecution
from .file_object import FileObjectClient

class NotebookInputOutputValidator(ABC):
    @abstractmethod
    def validate_input(
        self, notebook_config: NotebookConfig, parameters: Dict[str, Any]
    ) -> SchemaValidationResponse:
        pass

    @abstractmethod
    def validate_output(
        self, notebook_config: NotebookConfig, output: str
    ) -> SchemaValidationResponse:
        pass

class NotebookOutputReader(ABC):

    @abstractmethod
    def get_output(self, notebook: NotebookNode) -> OutputResult:
        pass

class NotebookConverter(ABC):

    @abstractmethod
    def convert_notebook_to_html(
        self, notebook: NotebookNode, report_mode: bool
    ) -> str:
        pass

    @abstractmethod
    def convert_notebook_to_str(self, notebook: NotebookNode) -> str:
        pass

class NotebookExecutionRepository(ABC):

    @abstractmethod
    async def get(self, execution_id: str) -> NotebookExecution:
        pass

    @abstractmethod
    async def save(self, execution: NotebookExecution) -> None:
        pass

    @abstractmethod
    async def create(self, execution: NotebookExecution) -> None:
        pass

class NotebookParameterizier(ABC):

    @abstractmethod
    def parameterize_notebook(
        self, notebook_config: NotebookConfig, parameters: Dict[str, Any]
    ) -> NotebookNode:
        pass

class NotebookRepository(ABC):

    @abstractmethod
    async def get(self, notebook_id: str) -> NotebookConfig:
        pass

    @abstractmethod
    async def iter_notebook_ids(self) -> AsyncIterable[str]:
        pass


class NotebookExecutionTaskHandler(ABC):

    @abstractmethod
    async def submit_execution_task(
        self,
        execution_id: str,
        deps: "DependencyBag"
    ):
        pass

class NotebookExecutionFileNamer(ABC):

    @abstractmethod
    def get_ipynb_name(self, execution: NotebookExecution) -> str:
        pass

    @abstractmethod
    def get_html_name(self, execution: NotebookExecution) -> str:
        pass

    @abstractmethod
    def get_html_report_name(self, execution: NotebookExecution) -> str:
        pass

    @abstractmethod
    def get_output_name(self, execution: NotebookExecution) -> str:
        pass

    @abstractmethod
    def get_exception_name(self, execution: NotebookExecution) -> str:
        pass


class NotebookExeuctor(ABC):
    @abstractmethod
    def get_kernelspec_language(self) -> str:
        pass

    @abstractmethod
    async def execute_notebook_async(self, notebook: NotebookNode) -> Optional[str]:
        """Executes a notebook in place. Returns an exception string if any.

        Args:
            notebook (NotebookNode): notebook to execute

        Returns:
            Optional[str]: exception
        """
        pass

@dataclass
class DependencyBag:
    notebook_execution_repository: NotebookExecutionRepository
    notebook_repository: NotebookRepository
    file_obj_client: FileObjectClient
    notebook_converter: NotebookConverter
    notebook_parameterizier: NotebookParameterizier
    notebook_executor: NotebookExeuctor
    notebook_output_reader: NotebookOutputReader
    notebook_input_output_validator: NotebookInputOutputValidator
    notebook_execution_task_handler: NotebookExecutionTaskHandler
    notebook_execution_file_namer: NotebookExecutionFileNamer

class ApplicationBuilder(ABC):

    @abstractmethod
    def build(self) -> DependencyBag:
        pass