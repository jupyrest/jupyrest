from pathlib import Path
from typing import Optional
from jupyrest.default_impl.builder import ModelSet
from ...default_impl.builder import DefaultApplicationBuilder
from .file_object_client import InMemoryFileObjectClient
from .execution_repository import InMemoryNotebookExecutionRepository


class InMemoryApplicationBuilder(DefaultApplicationBuilder):

    def __init__(self, notebooks_dir: Path, models: Optional[ModelSet] = {}) -> None:
        notebook_execution_repository = InMemoryNotebookExecutionRepository()
        file_object_client = InMemoryFileObjectClient()
        super().__init__(
            notebooks_dir=notebooks_dir,
            notebook_execution_repository=notebook_execution_repository,
            file_object_client=file_object_client,
            models=models
        )