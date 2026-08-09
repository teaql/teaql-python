import pytest
from teaql.core.eval import LoadState, EvalResult, EvalResultType

class Company:
    def __init__(self, name: str = None, load_state: LoadState = None):
        self.name = name
        self.__load_state = load_state or LoadState.NotLoaded()

    def eval_name(self) -> EvalResult[str]:
        if not self.__load_state.is_loaded("name"):
            return EvalResult.NotLoaded("name", "name")
        if self.name is not None:
            return EvalResult.Value(self.name)
        return EvalResult.Null()

class Platform:
    def __init__(self, company: Company = None, load_state: LoadState = None):
        self.company = company
        self.__load_state = load_state or LoadState.NotLoaded()

    def eval_company(self) -> EvalResult[Company]:
        if not self.__load_state.is_loaded("company"):
            return EvalResult.NotLoaded("company", "company")
        if self.company is not None:
            return EvalResult.Value(self.company)
        return EvalResult.Null()

class User:
    def __init__(self, platform: Platform = None, load_state: LoadState = None):
        self.platform = platform
        self.__load_state = load_state or LoadState.NotLoaded()

    def eval_platform(self) -> EvalResult[Platform]:
        if not self.__load_state.is_loaded("platform"):
            return EvalResult.NotLoaded("platform", "platform")
        if self.platform is not None:
            return EvalResult.Value(self.platform)
        return EvalResult.Null()

def test_eval_tracking_chain_perfect_path():
    company = Company(name=None, load_state=LoadState.NotLoaded())
    platform = Platform(company=company, load_state=LoadState.FullyLoaded())
    user = User(platform=platform, load_state=LoadState.FullyLoaded())

    result = user.eval_platform().and_then(
        "platform", lambda p: p.eval_company().and_then(
            "company", lambda c: c.eval_name()
        )
    )

    assert result.result_type == EvalResultType.NotLoaded
    assert result.attempted_path == "platform.company.name"

def test_eval_tracking_chain_middle_break():
    platform = Platform(company=None, load_state=LoadState.NotLoaded())
    user = User(platform=platform, load_state=LoadState.FullyLoaded())

    result = user.eval_platform().and_then(
        "platform", lambda p: p.eval_company().and_then(
            "company", lambda c: c.eval_name()
        )
    )

    assert result.result_type == EvalResultType.NotLoaded
    assert result.attempted_path == "platform.company"

def test_eval_tracking_chain_normal_null():
    company = Company(name=None, load_state=LoadState.FullyLoaded())
    platform = Platform(company=company, load_state=LoadState.FullyLoaded())
    user = User(platform=platform, load_state=LoadState.FullyLoaded())

    result = user.eval_platform().and_then(
        "platform", lambda p: p.eval_company().and_then(
            "company", lambda c: c.eval_name()
        )
    )

    assert result.result_type == EvalResultType.Null
