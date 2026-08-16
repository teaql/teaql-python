from typing import Callable, Optional, Generic, TypeVar, Any

R = TypeVar('R')
T = TypeVar('T')
U = TypeVar('U')
E = TypeVar('E', bound=Exception)

class SafeExpression(Generic[R, T]):
    def __init__(self, root: R, evaluator: Callable[[R], Optional[T]]):
        self._root = root
        self._evaluator = evaluator

    @classmethod
    def value(cls, root: R) -> 'SafeExpression[R, R]':
        return cls(root, lambda x: x)

    def eval(self) -> Optional[T]:
        return self._evaluator(self._root)

    def eval_with(self, root: R) -> Optional[T]:
        return self._evaluator(root)

    def apply(self, mapper: Callable[[T], U]) -> 'SafeExpression[R, U]':
        def _eval(root: R) -> Optional[U]:
            val = self._evaluator(root)
            if val is not None:
                return mapper(val)
            return None
        return SafeExpression(self._root, _eval)

    def apply_optional(self, mapper: Callable[[T], Optional[U]]) -> 'SafeExpression[R, U]':
        def _eval(root: R) -> Optional[U]:
            val = self._evaluator(root)
            if val is not None:
                return mapper(val)
            return None
        return SafeExpression(self._root, _eval)

    def or_if_null(self, default_value: T) -> T:
        val = self.eval()
        return val if val is not None else default_value

    def or_else_with(self, default_value_fn: Callable[[], T]) -> T:
        val = self.eval()
        return val if val is not None else default_value_fn()

    def or_else_throw(self, error_fn: Callable[[], E]) -> T:
        val = self.eval()
        if val is None:
            raise error_fn()
        return val

    def is_null(self) -> bool:
        return self.eval() is None

    def is_not_null(self) -> bool:
        return self.eval() is not None

    def is_empty(self) -> bool:
        val = self.eval()
        if val is None:
            return True
        if hasattr(val, '__len__'):
            return len(val) == 0
        return False

    def is_not_empty(self) -> bool:
        return not self.is_empty()

    def when_is_null(self, fn: Callable[[], None]) -> None:
        if self.is_null():
            fn()

    def when_is_not_null(self, consumer: Callable[[T], None]) -> None:
        val = self.eval()
        if val is not None:
            consumer(val)

    def when_is_empty(self, fn: Callable[[], None]) -> None:
        if self.is_empty():
            fn()

    def when_not_empty(self, consumer: Callable[[T], None]) -> None:
        val = self.eval()
        if val is not None and not self.is_empty():
            consumer(val)
