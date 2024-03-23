from abc import abstractmethod, ABC
import nbformat
from typing import Optional, Dict, Any, Generator
from pathlib import Path
import json
from pydantic import BaseModel, Field
from nbformat.notebooknode import NotebookNode
from papermill import __version__
from papermill.iorw import load_notebook_node
import logging
from jupyrest.nbschema import NotebookSchemaProcessor

from .notebook_config import NotebookConfig, NotebookConfigFile

logger = logging.getLogger(__name__)


class BaseResolver(ABC):
    @abstractmethod
    def resolve_notebook(self, notebook_id: str) -> nbformat.NotebookNode:
        pass

    @abstractmethod
    def resolve_config(self, notebook_id: str) -> NotebookConfig:
        pass

    @abstractmethod
    def exists(self, notebook_id: str) -> bool:
        ...

    @abstractmethod
    def iter_notebook_ids(self) -> Generator[str, None, None]:
        pass


class LocalDirectoryResolver(BaseResolver):
    def __init__(self, notebooks_dir: Path, refresh: bool = True):
        if not notebooks_dir.exists() or not notebooks_dir.is_dir():
            raise ValueError(f"{notebooks_dir} needs to be a valid directory")
        self._notebooks_dir = notebooks_dir
        self._configs: Dict[str, NotebookConfig] = {}
        if refresh:
            self.refresh()

    def get_notebook_path_from_config_path(self, config_path: Path) -> Path:
        return Path(str(config_path).replace(".config.json", ".ipynb"))

    def notebook_config_from_file(self, config_path: Path) -> NotebookConfig:
        notebook_path = self.get_notebook_path_from_config_path(config_path=config_path)
        notebook_config_file = NotebookConfigFile.parse_raw(notebook_path.read_text())
        notebook_id = notebook_config_file.id or notebook_path.relative_to(
            self.notebooks_dir
        ).as_posix().removesuffix(".ipynb")
        notebook_config = NotebookConfig(
            id=notebook_id,
            notebook_path=notebook_path.as_posix(),
            input=notebook_config_file.input,
            output=notebook_config_file.output,
        )
        return notebook_config

    def refresh(self):
        self._configs.clear()
        for config_path in self.notebooks_dir.glob("**/*.config.json"):
            notebook_path = self.get_notebook_path_from_config_path(
                config_path=config_path
            )
            if notebook_path.exists() and notebook_path.is_file():
                notebook_config = self.notebook_config_from_file(
                    config_path=config_path
                )
                self._configs[notebook_config.id] = notebook_config

    @property
    def notebooks_dir(self) -> Path:
        return self._notebooks_dir

    def resolve_notebook(self, notebook_id: str) -> nbformat.NotebookNode:
        notebook_config = self.resolve_config(notebook_id=notebook_id)
        return notebook_config.load_notebook_node()

    def exists(self, notebook_id: str) -> bool:
        return notebook_id in self._configs

    def resolve_config(self, notebook_id: str) -> NotebookConfig:
        return self._configs[notebook_id]

    def iter_notebook_ids(self) -> Generator[str, None, None]:
        yield from self._configs.keys()
