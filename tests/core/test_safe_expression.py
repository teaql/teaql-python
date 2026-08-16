import pytest
from teaql.core.safe_expression import SafeExpression

def test_safe_expression_eval_with_uses_the_supplied_root():
    expression = SafeExpression(2, lambda root: root * 3)
    assert expression.eval() == 6
    assert expression.eval_with(4) == 12

def test_safe_expression_apply_optional_short_circuits_remaining_mappers():
    optional_calls = [0]
    remaining_calls = [0]
    
    def first_mapper(x):
        optional_calls[0] += 1
        return None
        
    def second_mapper(x):
        remaining_calls[0] += 1
        return x * 2

    expression = SafeExpression.value(5).apply_optional(first_mapper).apply(second_mapper)

    assert expression.eval() is None
    assert optional_calls[0] == 1
    assert remaining_calls[0] == 0

def test_safe_expression_lazy_fallback_and_error_only_run_for_missing_values():
    present_fallback_calls = [0]
    present = SafeExpression.value(7)
    
    def present_fallback():
        present_fallback_calls[0] += 1
        return 9
        
    assert present.or_else_with(present_fallback) == 7
    assert present_fallback_calls[0] == 0
    assert present.or_else_throw(lambda: Exception("unused error")) == 7

    missing = SafeExpression(None, lambda root: None)
    missing_fallback_calls = [0]
    
    def missing_fallback():
        missing_fallback_calls[0] += 1
        return 9
        
    assert missing.or_else_with(missing_fallback) == 9
    assert missing_fallback_calls[0] == 1
    
    with pytest.raises(Exception, match="missing value"):
        missing.or_else_throw(lambda: Exception("missing value"))

def test_or_if_null_returns_value_or_fallback():
    assert SafeExpression.value(7).or_if_null(9) == 7
    assert SafeExpression(None, lambda root: None).or_if_null(9) == 9

def test_safe_expression_callbacks_only_run_for_their_matching_branch():
    present = SafeExpression.value("teaql")
    present_null_calls = [0]
    present_value = [None]
    
    present.when_is_null(lambda: present_null_calls.__setitem__(0, present_null_calls[0] + 1))
    present.when_is_not_null(lambda value: present_value.__setitem__(0, value))
    
    assert present_null_calls[0] == 0
    assert present_value[0] == "teaql"

    missing = SafeExpression(None, lambda root: None)
    missing_null_calls = [0]
    missing_value_calls = [0]
    
    missing.when_is_null(lambda: missing_null_calls.__setitem__(0, missing_null_calls[0] + 1))
    missing.when_is_not_null(lambda value: missing_value_calls.__setitem__(0, missing_value_calls[0] + 1))
    
    assert missing_null_calls[0] == 1
    assert missing_value_calls[0] == 0
