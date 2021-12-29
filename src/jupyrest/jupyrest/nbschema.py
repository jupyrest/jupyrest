import json
from nbformat.notebooknode import NotebookNode
import scrapbook as sb
from jsonschema import Draft7Validator, RefResolver
from jsonschema.exceptions import best_match
from typing import Optional, Dict, Type, Union, Any, Set
from urllib.parse import urlparse
from pydantic import BaseModel
from datetime import datetime, date
from papermill.translators import papermill_translators, PythonTranslator
from enum import Enum


class ConfigSections(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


NotebookConfig = Dict


class SchemaValidationResponse(BaseModel):
    is_valid: bool
    error: Optional[str] = None


class NbSchemaBase(BaseModel):
    """
    Base class for all NbSchema models.
    Inherits from Pydantic BaseModel.
    """

    pass


class ModelCollection:
    """
    Stores NbSchemaBase implementations along with their aliases.
    """

    def __init__(self) -> None:
        self._map: Dict[str, Type[NbSchemaBase]] = {}

    def add_model(self, alias: str, model_type: Type[NbSchemaBase], overwrite=False):
        """
        Add a model class and its alias to the collection.
        Duplicate aliases will be a no-op unless overwrite is True.
        """
        if alias not in self._map or overwrite:
            self._map[alias] = model_type

    def has_alias(self, alias: str) -> bool:
        return alias in self._map

    def get_model(self, alias: str) -> Type[NbSchemaBase]:
        if not self.has_alias(alias=alias):
            raise KeyError(f"Model for alias {alias} not found.")
        return self._map[alias]

    def is_empty(self) -> bool:
        return len(self._map.keys()) == 0


class NbSchemaEncoder(json.JSONEncoder):
    """
    JSONEncoder that can encode NbSchemaBase objects to json().
    This also encodes datetime objects to strings in iso format.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, NbSchemaBase):
            return json.loads(o.json())
        elif isinstance(o, (datetime, date)):
            return o.isoformat()
        else:
            return json.JSONEncoder.default(self, o)


class NbSchemaTranslator(PythonTranslator):
    """
    Translator for NbSchemaBase objects.
    """

    @classmethod
    def translate(cls, val):
        if isinstance(val, NbSchemaBase):
            return f"{val!r}"
        return super().translate(val)


class OutputResult(BaseModel):
    present: bool
    json_str: str


class NotebookSchemaProcessor:

    OUTPUTS_KEY = "nbschema_outputs"
    SCHEME = "nbschema"

    def __init__(self, models: Optional[ModelCollection] = None) -> None:
        self._models = models or ModelCollection()
        self._ref_resolver = RefResolver(
            "", {}, handlers={self.SCHEME: self._resolve_ref}
        )
        papermill_translators.register("python", NbSchemaTranslator)

    @classmethod
    def _uri_to_alias(cls, uri: str):
        scheme = urlparse(uri).scheme
        if scheme != cls.SCHEME:
            raise ValueError(f"Invalid uri scheme {scheme}")
        return uri.replace(f"{cls.SCHEME}://", "")

    def _get_validator(self, schema: Optional[Dict] = None):
        Draft7Validator.check_schema(schema)
        if not self._models.is_empty():
            return Draft7Validator(schema=schema, resolver=self._ref_resolver)
        else:
            return Draft7Validator(schema=schema)

    def _validate_instance(
        self, instance: Optional[Dict], schema: Optional[Dict] = None
    ) -> SchemaValidationResponse:
        # if we have a schema to validate against
        if schema is not None:
            # Check that this is a valid JSONSchema. Raise an exception if it is not.
            validator = self._get_validator(schema=schema)
            error = best_match(validator.iter_errors(instance=instance))
            if error is not None:
                return SchemaValidationResponse(is_valid=False, error=str(error))
        return SchemaValidationResponse(is_valid=True)

    def _resolve_ref(self, ref: str):
        alias = self._uri_to_alias(uri=ref)
        return self._models.get_model(alias=alias).schema()

    @property
    def models(self):
        return self._models

    def inject_model_refs(self, schema: Dict, payload: Dict):
        """
        This function assumes that `payload` adheres to the JSON Schema
        defined by `schema`.

        Does not support "anyOf", "allOf", "oneOf" or "contains".

        Recursively walk the key value pairs of each of the input
        dicts (schema and payload) in lockstep.

        Wherever `schema` has a $ref to an nbschema model, replace
        the corresponding object in `payload` with a instance of the
        NbSchemaBase class that is referenced. NbSchemaBase objects know
        how to create themselves from a dict.

        Returns a payload object with NbSchemaBase objects injected if any.
        """
        if schema is None or payload is None:
            return payload
        # Case 1: schema is a $ref to nbschema://
        ref = schema.get("$ref", None)
        if ref is not None:
            u = urlparse(ref)
            if u.scheme == "nbschema":
                alias = self._uri_to_alias(uri=ref)
                klass = self._models.get_model(alias=alias)
                obj = klass.parse_obj(payload)
                return obj

        # Case 2: schema "type" is an object or array.
        schema_type = schema.get("type", None)
        if schema_type is not None:
            if schema_type == "object":
                # if object, recursive call on kv pairs
                props = schema.get("properties", {})
                for prop in props:
                    if prop in payload:
                        new_schema = props[prop]
                        new_payload = payload[prop]
                        payload[prop] = self.inject_model_refs(new_schema, new_payload)
                return payload
            elif schema_type == "array":
                # if list, recursive call on list items
                item_schema = schema.get("items", None)
                if item_schema is not None:
                    objs = []
                    for item in payload:
                        obj = self.inject_model_refs(item_schema, item)
                        objs.append(obj)
                    return objs
        return payload

    def validate_input(
        self, input: Dict, notebook_config: Optional[NotebookConfig]
    ) -> SchemaValidationResponse:
        input_schema = (
            notebook_config.get(ConfigSections.INPUT, None) if notebook_config else None
        )
        return self._validate_instance(instance=input, schema=input_schema,)

    def validate_output(
        self, output, notebook_config: Optional[NotebookConfig]
    ) -> SchemaValidationResponse:
        output_schema = (
            notebook_config.get(ConfigSections.OUTPUT, None)
            if notebook_config
            else None
        )
        return self._validate_instance(instance=output, schema=output_schema)

    @classmethod
    def save_output(cls, data: Union[str, NbSchemaBase], **kwargs):
        """
        Simple wrapper around scrapbook's glue() function.
        The only difference is that the `name` parameter
        is set to OUTPUTS_KEY. The data to save should
        be a string compatible with the "application/json"
        mimetype or it must be an NbSchemaBase.

        Usage (in a notebook):
        >>> save_output(data='{"json_key": "json_value"}')
        >>> save_output(data=json.dumps(my_obj))

        :param data: data to save
        :param kwagrs: passed on to scrapbook.glue
        """
        json_str = None
        if isinstance(data, str):
            json_str = data
        else:
            json_str = json.dumps(data, cls=NbSchemaEncoder)
        # test that this string is valid JSON
        json.loads(json_str)
        sb.glue(cls.OUTPUTS_KEY, json_str, **kwargs)

    def get_notebook_output(self, notebook: NotebookNode) -> OutputResult:
        """
        Get outputs from an executed notebook.
        """
        nb = sb.read_notebook(notebook)
        if self.OUTPUTS_KEY in nb.scraps.data_dict:
            json_str = nb.scraps.data_dict[self.OUTPUTS_KEY]
            return OutputResult(present=True, json_str=json_str)
        else:
            return OutputResult(present=False, json_str="")
