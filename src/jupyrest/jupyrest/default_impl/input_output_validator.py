from typing import Dict, Any
import json

from ..contracts import NotebookInputOutputValidator
from ..nbschema import NotebookSchemaProcessor, SchemaValidationResponse
from ..notebook_config import NotebookConfig



class DefaultNotebookInputOutputValidator(NotebookInputOutputValidator):
    
    def __init__(self, nbschema: NotebookSchemaProcessor) -> None:
        self.nbschema = nbschema

    def validate_input(
        self, notebook_config: NotebookConfig, parameters: Dict[str, Any]
    ) -> SchemaValidationResponse:
        return self.nbschema.validate_instance(instance=parameters, schema=notebook_config.resolved_input_schema)

    def validate_output(
        self, notebook_config: NotebookConfig, output: str
    ) -> SchemaValidationResponse:
        return self.nbschema.validate_instance(instance=json.loads(output), schema=notebook_config.resolved_output_schema)