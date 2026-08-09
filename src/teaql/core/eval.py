from enum import Enum, auto
from typing import Set, Any, Generic, TypeVar, Callable

class LoadStateType(Enum):
    NotLoaded = auto()
    Partial = auto()
    FullyLoaded = auto()

class LoadState:
    def __init__(self, state_type: LoadStateType = LoadStateType.NotLoaded, fields: Set[str] = None):
        self.state_type = state_type
        self.fields = fields or set()

    @classmethod
    def NotLoaded(cls) -> 'LoadState':
        return cls(LoadStateType.NotLoaded)

    @classmethod
    def Partial(cls, fields: Set[str]) -> 'LoadState':
        return cls(LoadStateType.Partial, fields)

    @classmethod
    def FullyLoaded(cls) -> 'LoadState':
        return cls(LoadStateType.FullyLoaded)

    def is_loaded(self, field_or_relation: str) -> bool:
        if self.state_type == LoadStateType.NotLoaded:
            return False
        if self.state_type == LoadStateType.FullyLoaded:
            return True
        return field_or_relation in self.fields

T = TypeVar('T')
U = TypeVar('U')

class EvalResultType(Enum):
    Value = auto()
    Null = auto()
    NotLoaded = auto()

class EvalResult(Generic[T]):
    def __init__(self, result_type: EvalResultType, value: T = None, failed_node: str = None, attempted_path: str = None):
        self.result_type = result_type
        self.value = value
        self.failed_node = failed_node
        self.attempted_path = attempted_path

    @classmethod
    def Value(cls, value: T) -> 'EvalResult[T]':
        return cls(EvalResultType.Value, value=value)

    @classmethod
    def Null(cls) -> 'EvalResult[T]':
        return cls(EvalResultType.Null)

    @classmethod
    def NotLoaded(cls, failed_node: str, attempted_path: str) -> 'EvalResult[T]':
        return cls(EvalResultType.NotLoaded, failed_node=failed_node, attempted_path=attempted_path)

    def and_then(self, field_name: str, f: Callable[[T], 'EvalResult[U]']) -> 'EvalResult[U]':
        if self.result_type == EvalResultType.Value:
            res = f(self.value)
            if res.result_type == EvalResultType.NotLoaded:
                new_path = res.attempted_path
                if new_path == field_name:
                    pass
                elif not new_path:
                    new_path = field_name
                else:
                    new_path = f"{field_name}.{new_path}"
                return EvalResult.NotLoaded(res.failed_node, new_path)
            return res
        elif self.result_type == EvalResultType.Null:
            return EvalResult.Null()
        else:
            return EvalResult.NotLoaded(self.failed_node, self.attempted_path)

    def map(self, f: Callable[[T], U]) -> 'EvalResult[U]':
        if self.result_type == EvalResultType.Value:
            return EvalResult.Value(f(self.value))
        elif self.result_type == EvalResultType.Null:
            return EvalResult.Null()
        else:
            return EvalResult.NotLoaded(self.failed_node, self.attempted_path)
