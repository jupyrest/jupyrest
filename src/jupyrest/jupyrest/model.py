from pydantic import BaseModel, parse_obj_as
from typing import Callable, Type, Dict, cast
from typing_extensions import Self
import json

named_model_registry: Dict[str, Type["NamedModel"]] = {}


class NamedModelConflict(Exception):
    pass


class NamedModel(BaseModel):
    """A NamedModel is a type that has a name. The name is
    stored in a `__ns__` class property. This information
    is a part of the objects JSON schema representation.

    Make a NamedModel:

    ```
    class MyNamedModel(NamedModel):
        prop1: str
        prop2: int

        class Config:
            __ns__ = "models/MyNamedModel"
    ```

    The benefit of a NamedModel is that it knows how to
    take a generic object and deserialize it to the correct
    subclass.

    ```
    import json

    # create the object
    model = MyNamedModel(prop1="foo", prop2=5)
    # convert to JSON string, then read it back as a dict
    model_json = json.loads(model.json())

    parsed_model = NamedModel.parse_obj(model_json)
    assert isinstance(parsed_model, MyNamedModel)
    ```
    """

    @classmethod
    def _get_ns_key(cls) -> str:
        if hasattr(cls.Config, "NS_KEY"):
            return cls.Config.NS_KEY
        else:
            return NamedModel.Config.NS_KEY

    @classmethod
    def get_class_namespace(cls):
        """Get the namespace for this class."""
        if hasattr(cls.Config, "__ns__"):
            return str(getattr(cls.Config, "__ns__"))
        else:
            raise ValueError(f"Class {cls} does not have a namespace")

    @classmethod
    def _iter_subclasses(cls):
        """Iterate over the subclasses for a
        particular type `cls` including `cls` itself.
        """
        global named_model_registry
        if cls is not NamedModel:
            if cls.get_class_namespace() not in named_model_registry:
                named_model_registry[cls.get_class_namespace()] = cls

            yield cls
        for sk in cls.__subclasses__():
            yield from sk._iter_subclasses()

    def dict(self, *args, **kwargs):
        """When we convert to a dict, we want
        to save the name of the model.
        """
        d = super().dict(*args, **kwargs)
        NS_KEY = self._get_ns_key()
        d[NS_KEY] = self.get_class_namespace()
        return d

    def json(self, *args, **kwargs):
        d = self.__config__.json_loads(super().json(*args, **kwargs))
        NS_KEY = self._get_ns_key()
        d[NS_KEY] = self.get_class_namespace()
        return self.__config__.json_dumps(d)

    @classmethod
    def parse_obj(cls, data, *args, **kwargs) -> Self:
        NS_KEY = cls._get_ns_key()

        def data_has_ns_info(o):
            """This will tell us whether we should
            try parsing `data` or not
            """
            return isinstance(o, dict) and NS_KEY in data and isinstance(o[NS_KEY], str)

        def subclass_has_ns_info(sk):
            return hasattr(sk, NS_KEY) and isinstance(getattr(sk, NS_KEY), str)

        def subclass_has_name(name: str) -> Callable[[Type["NamedModel"]], bool]:
            def _check_name(sk: Type["NamedModel"]) -> bool:
                return sk.get_class_namespace() == name

            return _check_name

        def get_subclass_for_ns(ns: str):
            if ns not in named_model_registry:
                list(cls._iter_subclasses())
            return named_model_registry.get(ns, None)

        # if data has the namespace information we are looking for
        if data_has_ns_info(data):
            subclass = get_subclass_for_ns(data[NS_KEY])
            if subclass is not None:
                return cast(Self, parse_obj_as(subclass, data))

        return parse_obj_as(cls, data)

    class Config:
        # the name of this type (the namespace)
        __ns__: str
        NS_KEY: str = "__ns__"

        @staticmethod
        def schema_extra(schema, model: Type["NamedModel"]) -> None:
            """Augment the json schema to add the required
            namespace property.
            """
            NS_KEY = model._get_ns_key()

            # by default, the description is the class docstring
            # this is not relevant so we will remove it
            if "description" in schema and schema["description"] is not None:
                del schema["description"]

            if "properties" in schema and schema["properties"] is not None:
                schema["properties"][NS_KEY] = {"type": "string"}
            else:
                schema["required"] = {NS_KEY: {"type": "string"}}

            if "required" in schema and schema["required"] is not None:
                schema["required"].append(NS_KEY)
            else:
                schema["required"] = [NS_KEY]
