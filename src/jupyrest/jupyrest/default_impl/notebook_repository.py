from pathlib import Path
from typing import Dict

from ..contracts import NotebookRepository
from ..nbschema import NotebookSchemaProcessor
from ..notebook_config import NotebookConfig, NotebookConfigFile
from ..error import NotebookNotFound

class DefaultNotebookRepository(NotebookRepository):

    def __init__(self, notebooks_dir: Path, nbschema: NotebookSchemaProcessor) -> None:
        if not notebooks_dir.exists() or not notebooks_dir.is_dir():
            raise ValueError(f"{notebooks_dir} needs to be a valid directory")
        self.notebooks_dir = notebooks_dir
        self.nbschema = nbschema
        self._configs: Dict[str, NotebookConfig] = {}
        self.refresh()

    def refresh(self):
        self._configs.clear()
        config_paths = list(self.notebooks_dir.glob("**/*.config.json"))
        for config_path in config_paths:
            notebook_path = self.get_notebook_path_from_config_path(
                config_path=config_path
            )
            if notebook_path.exists() and notebook_path.is_file():
                notebook_config = self.notebook_config_from_file(
                    config_path=config_path
                )
                self._configs[notebook_config.id] = notebook_config

    def get_notebook_path_from_config_path(self, config_path: Path) -> Path:
        return Path(str(config_path).replace(".config.json", ".ipynb"))

    def notebook_config_from_file(self, config_path: Path) -> NotebookConfig:
        notebook_path = self.get_notebook_path_from_config_path(config_path=config_path)
        notebook_config_file = NotebookConfigFile.parse_raw(config_path.read_text())
        notebook_id = (
            notebook_config_file.id
            or notebook_path.relative_to(self.notebooks_dir).as_posix().removesuffix(".ipynb")
        )
        resolved_input = self.nbschema.fix_schemas(schema=notebook_config_file.input, add_model_definitions=True)
        resolved_output = self.nbschema.fix_schemas(schema=notebook_config_file.output, add_model_definitions=True)
        notebook_config = NotebookConfig(
            id=notebook_id,
            notebook_path=notebook_path.as_posix(),
            input=notebook_config_file.input,
            output=notebook_config_file.output,
            resolved_input_schema=resolved_input,
            resolved_output_schema=resolved_output
        )
        return notebook_config

    async def get(self, notebook_id: str) -> NotebookConfig:
        if notebook_id in self._configs:
            return self._configs[notebook_id]
        else:
            raise NotebookNotFound(notebook_id=notebook_id) 

    async def iter_notebook_ids(self):
        for notebook_id in self._configs.keys():
            yield notebook_id