import warnings

warnings.simplefilter("ignore", FutureWarning)
warnings.simplefilter("ignore", DeprecationWarning)

from importlib.resources import files

project_root = files("jupyrest")

from .nbschema import NotebookSchemaProcessor

save_output = NotebookSchemaProcessor.save_output
