import pytest
from teaql.core.eval import LoadState, LoadStateType, EvalResult, EvalResultType

def test_load_state():
    ls = LoadState.NotLoaded()
    assert ls.state_type == LoadStateType.NotLoaded
    assert not ls.is_loaded("field")

    ls = LoadState.FullyLoaded()
    assert ls.state_type == LoadStateType.FullyLoaded
    assert ls.is_loaded("field")

    ls = LoadState.Partial({"field1", "field2"})
    assert ls.state_type == LoadStateType.Partial
    assert ls.is_loaded("field1")
    assert not ls.is_loaded("field3")

def test_eval_result_creation():
    r1 = EvalResult.Value(10)
    assert r1.result_type == EvalResultType.Value
    assert r1.value == 10
    
    r2 = EvalResult.Null()
    assert r2.result_type == EvalResultType.Null
    assert r2.value is None

    r3 = EvalResult.NotLoaded("User", "address")
    assert r3.result_type == EvalResultType.NotLoaded
    assert r3.failed_node == "User"
    assert r3.attempted_path == "address"

def test_eval_result_map():
    r1 = EvalResult.Value(10)
    r2 = r1.map(lambda x: x * 2)
    assert r2.result_type == EvalResultType.Value
    assert r2.value == 20
    
    r3 = EvalResult.Null().map(lambda x: x * 2)
    assert r3.result_type == EvalResultType.Null
    
    r4 = EvalResult.NotLoaded("U", "a").map(lambda x: x * 2)
    assert r4.result_type == EvalResultType.NotLoaded
    assert r4.attempted_path == "a"

def test_eval_result_and_then():
    def get_address(user_id):
        if user_id == 1:
            return EvalResult.Value("Main St")
        elif user_id == 2:
            return EvalResult.Null()
        else:
            return EvalResult.NotLoaded("Address", "street")

    r1 = EvalResult.Value(1).and_then("address", get_address)
    assert r1.result_type == EvalResultType.Value
    assert r1.value == "Main St"

    r2 = EvalResult.Value(2).and_then("address", get_address)
    assert r2.result_type == EvalResultType.Null

    r3 = EvalResult.Value(3).and_then("address", get_address)
    assert r3.result_type == EvalResultType.NotLoaded
    assert r3.attempted_path == "address.street"
    
    r4 = EvalResult.NotLoaded("U", "id").and_then("address", get_address)
    assert r4.result_type == EvalResultType.NotLoaded
    assert r4.attempted_path == "id"
    
    r5 = EvalResult.Null().and_then("address", get_address)
    assert r5.result_type == EvalResultType.Null
