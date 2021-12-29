import warnings

warnings.simplefilter("ignore", FutureWarning)
warnings.simplefilter("ignore", DeprecationWarning)

from .nbschema import NotebookSchemaProcessor

save_output = NotebookSchemaProcessor.save_output
