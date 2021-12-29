from abc import abstractmethod, ABC
import nbformat
from typing import Optional, Dict, Any
from pathlib import Path
import json

from nbformat.notebooknode import NotebookNode
from .nbschema import NotebookConfig
from papermill import __version__
from opentelemetry import trace
from azure.storage.blob import ContainerClient

tracer = trace.get_tracer(__name__)


def load_notebook_node(nb: NotebookNode) -> NotebookNode:
    """Returns a notebook object with papermill and cell tag metadata.
    This function was taken from papermill.iorw.load_notebook_node.

    Args:
        nb (NotebookNode)

    Returns:
        NotebookNode
    """

    if not hasattr(nb.metadata, "papermill"):
        nb.metadata["papermill"] = {
            "default_parameters": dict(),
            "parameters": dict(),
            "environment_variables": dict(),
            "version": __version__,
        }

    for cell in nb.cells:
        if not hasattr(cell.metadata, "tags"):
            cell.metadata["tags"] = []  # Create tags attr if one doesn't exist.

        if not hasattr(cell.metadata, "papermill"):
            cell.metadata["papermill"] = dict()

    return nb


class BaseResolver(ABC):
    @abstractmethod
    def resolve_notebook(self, notebook_id: str) -> Optional[nbformat.NotebookNode]:
        pass

    @abstractmethod
    def resolve_config(self, notebook_id: str) -> Optional[NotebookConfig]:
        pass


class LocalDirectoryResolver(BaseResolver):

    _config_cache: Optional[Dict[Path, Dict]] = None

    def __init__(self, notebooks_dir: Path):
        if not notebooks_dir.exists() or not notebooks_dir.is_dir():
            raise ValueError(f"{notebooks_dir} needs to be a valid directory")
        self._notebooks_dir = notebooks_dir

    @classmethod
    def _read_file(cls, path: Path) -> str:
        return path.read_bytes().decode("utf-8-sig")

    @classmethod
    def _read_config(cls, path: Path) -> Optional[NotebookConfig]:
        if not path.exists():
            return None
        if cls._config_cache is None:
            cls._config_cache = dict()
        if path not in cls._config_cache:
            text = cls._read_file(path=path)
            config_dict: Dict[str, Any] = json.loads(text)
            cls._config_cache[path] = config_dict
        return cls._config_cache[path]

    def get_notebook_file(self, notebook_id: str) -> Path:
        return self.notebooks_dir / f"{notebook_id}.ipynb"

    def get_config_file(self, notebook_id: str) -> Path:
        notebook_file = self.get_notebook_file(notebook_id=notebook_id)
        return notebook_file.parent / f"{notebook_file.stem}.config.json"

    @property
    def notebooks_dir(self) -> Path:
        return self._notebooks_dir

    def resolve_notebook(self, notebook_id: str) -> Optional[nbformat.NotebookNode]:
        notebook_file = self.get_notebook_file(notebook_id=notebook_id)
        if notebook_file.exists() and notebook_file.is_file():
            nb = nbformat.reads(
                notebook_file.read_text(), as_version=nbformat.NO_CONVERT
            )
            return load_notebook_node(nb=nb)

    def resolve_config(self, notebook_id: str) -> Optional[NotebookConfig]:
        config_file = self.get_config_file(notebook_id=notebook_id)
        return self._read_config(path=config_file)


class BlobNotFoundException(Exception):
    pass


class AzureStorageResolver(BaseResolver):
    def __init__(self, container_client: ContainerClient, prefix: Optional[str] = None):
        self.notebook_container_client = container_client
        self.prefix = prefix or ""

    def make_notebook_uri(self, notebook_id: str):
        return f"{self.prefix}{notebook_id}.ipynb"

    def make_config_uri(self, notebook_id: str):
        return f"{self.prefix}{notebook_id}.config.json"

    def get_blob_contents(self, uri: str) -> str:
        blob_client = self.notebook_container_client.get_blob_client(uri)

        if not blob_client.exists():
            raise BlobNotFoundException(f"Blob with uri {uri} does not exist")

        download_blob = blob_client.download_blob()
        blob_contents = download_blob.readall()
        if isinstance(blob_contents, bytes):
            blob_contents = blob_contents.decode()
        return blob_contents

    def resolve_notebook(self, notebook_id: str) -> Optional[nbformat.NotebookNode]:
        with tracer.start_as_current_span("azstorage.resolve_notebook"):
            notebook_obj: Optional[nbformat.NotebookNode] = None
            notebook_file_uri = f"{notebook_id}.ipynb"
            try:
                notebook_contents = self.get_blob_contents(notebook_file_uri)
                notebook_obj = nbformat.reads(
                    s=notebook_contents, as_version=nbformat.NO_CONVERT
                )
            except BlobNotFoundException:
                pass

            if notebook_obj is not None:
                notebook_obj = load_notebook_node(notebook_obj)
            return notebook_obj

    def resolve_config(self, notebook_id: str) -> Optional[NotebookConfig]:
        with tracer.start_as_current_span("azstorage.resolve_config"):
            config_dict: Optional[Dict[str, Any]] = None
            config_file_uri = f"{notebook_id}.config.json"
            try:
                config_contents = self.get_blob_contents(config_file_uri)
                config_dict = json.loads(config_contents)
            except BlobNotFoundException:
                pass

            return config_dict
