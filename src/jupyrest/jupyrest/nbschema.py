import json
from nbformat.notebooknode import NotebookNode
import scrapbook as sb
from jsonschema import Draft7Validator, RefResolver
from jsonschema.exceptions import best_match
from typing import Optional, Dict, Type, Union, Any, Set, List, Iterable
from pydantic.schema import schema as pydantic_schema
from unittest.mock import patch
from urllib.parse import urlparse
from pydantic import BaseModel
from datetime import datetime, date
from papermill.translators import papermill_translators, PythonTranslator
from enum import Enum
from copy import deepcopy
from .model import NamedModel

class SchemaValidationResponse(BaseModel):
    is_valid: bool
    error: Optional[str] = None


class NbSchemaBase(BaseModel):
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

    def has_model(self, model_type: Type[NbSchemaBase]) -> bool:
        return model_type in self._map.values()

    def get_alias(self, model_type: Type[NbSchemaBase]) -> str:
        for k, v in self._map.items():
            if v == model_type:
                return k
        raise KeyError(f"Alias for model {model_type} not found.")


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


class OutputResult(NamedModel):
    present: bool
    json_str: str

    class Config:
        __ns__ = "jupyrest.nbschema.OutputResult"


class NotebookSchemaProcessor:

    OUTPUTS_KEY = "nbschema_outputs"
    SCHEME = "nbschema"

    def __init__(self, models: Dict[str, Type[NbSchemaBase]]) -> None:
        self._models = ModelCollection()
        for model_alias, model_type in models.items():
            self._models.add_model(alias=model_alias, model_type=model_type)
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

    def _get_validator(self, schema: Dict):
        Draft7Validator.check_schema(schema)
        return Draft7Validator(schema=schema)


    def validate_instance(
        self, instance: Dict, schema: Dict
    ) -> SchemaValidationResponse:
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

    def fix_schemas(self, schema: Dict, add_model_definitions: bool) -> Dict:
        obj = deepcopy(schema)
        mc = self._models

        def get_ref_paths(obj: Dict) -> Dict[str, List[List[Union[str, int]]]]:

            ref_locs: Dict[str, List[List[Union[str, int]]]] = {}

            def add_ref(ref: str, path: List[Union[str, int]]):
                nonlocal ref_locs
                if ref in ref_locs:
                    ref_locs[ref].append(path)
                else:
                    ref_locs[ref] = [path]

            def get_ref_paths_inner(
                obj: Union[Dict, List], path: List[Union[str, int]]
            ):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        curr_path = path + [key]
                        if (
                            key == "$ref"
                            and isinstance(value, str)
                            and value.startswith("nbschema://")
                        ):
                            add_ref(ref=value, path=path)
                        elif isinstance(value, (list, dict)):
                            get_ref_paths_inner(obj=value, path=curr_path)
                elif isinstance(obj, list):
                    for index, value in enumerate(obj):
                        curr_path = path + [index]
                        if isinstance(value, (list, dict)):
                            get_ref_paths_inner(obj=value, path=curr_path)

            get_ref_paths_inner(obj=obj, path=[])

            return ref_locs

        def get_value(obj: Dict, path: List[Union[str, int]]):
            curr = obj
            for part in path:
                curr = curr[part]
            return curr

        def set_value(obj: Dict, ref_path: List[Union[str, int]], ref_value: str):
            curr = obj
            for part in ref_path:
                curr = curr[part]
            curr["$ref"] = ref_value

        def resolve_definitions(model_refs: Iterable[str]):
            model_name_map = {}
            models = []
            for model_ref in model_refs:
                alias = NotebookSchemaProcessor._uri_to_alias(uri=model_ref)
                model_type = mc.get_model(alias)
                model_name_map[model_type] = alias
                models.append(model_type)

            def new_get_model_name_map(*args, **kwargs):
                return model_name_map

            with patch(
                "pydantic.schema.get_model_name_map", new=new_get_model_name_map
            ):
                return pydantic_schema(models)

        def update_nbschema_refs(
            obj: Dict, ref_locs: Dict[str, List[List[Union[str, int]]]]
        ):
            for ref in ref_locs:
                alias = self._uri_to_alias(ref)
                for ref_path in ref_locs[ref]:
                    ref_value = f"#/definitions/{alias}"
                    set_value(obj=obj, ref_path=ref_path, ref_value=ref_value)

        def add_definitions(
            obj: Dict, ref_locs: Dict[str, List[List[Union[str, int]]]]
        ):
            definitions = resolve_definitions(model_refs=ref_locs.keys())
            if "definitions" in definitions:
                if "definitions" not in obj:
                    obj["definitions"] = {}
                obj["definitions"].update(definitions["definitions"])

        ref_locs = get_ref_paths(obj=obj)
        if add_model_definitions:
            add_definitions(obj=obj, ref_locs=ref_locs)
        update_nbschema_refs(obj=obj, ref_locs=ref_locs)

        return obj
