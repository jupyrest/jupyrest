from pydantic import BaseModel, parse_obj_as
from typing import Callable, Type, Dict


class NamedModelConflict(Exception):
    pass


class NamedModel(BaseModel):
    """A NamedModel is a type that has a name. The name is
    stored in a `__ns__` class property. This information
    is a part of the objects JSON schema representation.

    Make a NamedModel:

    ```
    class MyNamedModel(NamedModel):
        __ns__ = "models/MyNamedModel"

        prop1: str
        prop2: int
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

    # a mapping from namespaces -> subclasses of NamedModel
    __nsmap__: Dict[str, Type["NamedModel"]] = {}
    # the name of this type (the namespace)
    __ns__: str

    @classmethod
    def _iter_subclasses(cls):
        """Iterate over the subclasses for a
        particular type `cls` including `cls` itself.
        """
        yield cls
        for sk in cls.__subclasses__():
            yield from sk._iter_subclasses()

    def dict(self, *args, **kwargs):
        """When we convert to a dict, we want
        to save the name of the model.
        """
        d = super().dict(*args, **kwargs)
        d[self.Config.NS_KEY] = getattr(self, self.Config.NS_KEY)
        return d

    @classmethod
    def parse_obj(cls, data, *args, **kwargs):
        NS_KEY = cls.Config.NS_KEY

        def data_has_ns_info(o):
            """This will tell us whether we should
            try parsing `data` or not
            """
            return isinstance(o, dict) and NS_KEY in data and isinstance(o[NS_KEY], str)

        def subclass_has_ns_info(sk):
            return hasattr(sk, NS_KEY) and isinstance(getattr(sk, NS_KEY), str)

        def subclass_has_name(name: str) -> Callable[[Type["NamedModel"]], bool]:
            def _check_name(sk: Type["NamedModel"]) -> bool:
                return getattr(sk, NS_KEY) == name

            return _check_name

        def get_subclass_for_ns(ns: str):
            if ns not in NamedModel.__nsmap__:
                # find the correct subclass
                sks = filter(subclass_has_ns_info, cls._iter_subclasses())
                sks = filter(subclass_has_name(data[NS_KEY]), sks)
                sks = set(sks)

                # we should only have at most 1 subclass
                # for a given name
                if len(sks) > 1:
                    raise NamedModelConflict(f"{sks} have conflicting names {ns}")
                elif len(sks) == 1:
                    sk = sks.pop()
                    NamedModel.__nsmap__[ns] = sk
                else:
                    return None

            return NamedModel.__nsmap__[ns]

        # if data has the namespace information we are looking for
        if data_has_ns_info(data):
            subclass = get_subclass_for_ns(data[NS_KEY])
            if subclass is not None:
                return parse_obj_as(subclass, data)

        return parse_obj_as(cls, data)

    class Config:

        NS_KEY: str = "__ns__"

        @staticmethod
        def schema_extra(schema, model: Type["NamedModel"]) -> None:
            """Augment the json schema to add the required
            namespace property.
            """
            NS_KEY = model.Config.NS_KEY

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
