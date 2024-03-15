from typing import TypeVar, Type, Dict, Tuple, Any, cast

DepType = TypeVar("DepType")

NamedDependency = Tuple[str, Type]


class DependencyManager:
    def __init__(self):
        self._deps: Dict[NamedDependency, Any] = {}

    def register(self, name: str, dep: Any):
        named_dep: NamedDependency = (name, type(dep))
        if dep in self._deps:
            raise KeyError(f"Dependency {named_dep} already registered.")
        self._deps[named_dep] = dep

    def get(self, name: str, dep_type: Type[DepType]) -> DepType:
        named_dep: NamedDependency = (name, dep_type)
        if named_dep not in self._deps:
            raise KeyError(f"Dependency {named_dep} not found.")
        return cast(DepType, self._deps[named_dep])


depedencies = DependencyManager()
