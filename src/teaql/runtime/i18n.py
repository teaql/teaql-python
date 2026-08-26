from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import builtins
import json
from importlib.resources import files
from typing import Any, Mapping

@dataclass(frozen=True, eq=False)
class ObjectLocation:
    """A checker location whose source of truth is the canonical KSML path."""
    segments: tuple[tuple[str, Any], ...] = ()

    def property(self, name: str) -> ObjectLocation:
        return ObjectLocation(self.segments + (("property", name),))

    def index(self, value: int) -> ObjectLocation:
        return ObjectLocation(self.segments + (("index", value),))

    @builtins.property
    def model_path(self) -> str:
        return self._render(lambda value: value)

    @builtins.property
    def native_path(self) -> str:
        return self._render(lambda value: value)

    @builtins.property
    def instance_path(self) -> str:
        parts = []
        for kind, value in self.segments:
            text = str(value) if kind == "index" else _lower_camel(str(value))
            parts.append(text.replace("~", "~0").replace("/", "~1"))
        return "" if not parts else "/" + "/".join(parts)

    def _render(self, transform) -> str:
        result = ""
        for kind, value in self.segments:
            if kind == "index": result += f"[{value}]"
            else: result += ("." if result else "") + transform(str(value))
        return result

    def __str__(self) -> str:
        return self.native_path

    def __eq__(self, other) -> bool:
        if isinstance(other, ObjectLocation): return self.segments == other.segments
        if isinstance(other, str): return self.model_path == other
        return False

    def __hash__(self) -> int:
        return hash(self.segments)

    @classmethod
    def from_model_path(cls, path: str) -> ObjectLocation:
        location = cls()
        for part in filter(None, path.split(".")):
            location = location.property(part)
        return location

def _lower_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])

class UnsupportedLocaleError(ValueError):
    def __init__(self, code: str | None):
        super().__init__(f"Unsupported locale: {code}"); self.locale_code = code

class Locale(str, Enum):
    ENGLISH="en"; CHINESE_SIMPLIFIED="zh-CN"; CHINESE_TRADITIONAL="zh-TW"; JAPANESE="ja"
    KOREAN="ko"; GERMAN="de"; FRENCH="fr"; SPANISH="es"; PORTUGUESE="pt"; ARABIC="ar"
    THAI="th"; INDONESIAN="id"; FILIPINO="fil"; UKRAINIAN="uk"; VIETNAMESE="vi"
    @classmethod
    def parse(cls, code):
        if isinstance(code, cls): return code
        if not isinstance(code, str) or not code.strip(): raise UnsupportedLocaleError(code)
        normalized=code.strip().replace("_", "-").lower()
        for locale in cls:
            if locale.value.lower()==normalized: return locale
        alias=_ALIASES.get(normalized)
        if alias is None: raise UnsupportedLocaleError(code)
        return alias

_ALIASES={"en-us":Locale.ENGLISH,"en-gb":Locale.ENGLISH,"zh":Locale.CHINESE_SIMPLIFIED,
"zh-hans":Locale.CHINESE_SIMPLIFIED,"zh-sg":Locale.CHINESE_SIMPLIFIED,"cn":Locale.CHINESE_SIMPLIFIED,
"zh-hant":Locale.CHINESE_TRADITIONAL,"zh-hk":Locale.CHINESE_TRADITIONAL,"zh-mo":Locale.CHINESE_TRADITIONAL,
"tw":Locale.CHINESE_TRADITIONAL,"ja-jp":Locale.JAPANESE,"ko-kr":Locale.KOREAN,"de-de":Locale.GERMAN,
"fr-fr":Locale.FRENCH,"es-mx":Locale.SPANISH,"pt-br":Locale.PORTUGUESE,"pt-pt":Locale.PORTUGUESE,
"ar-sa":Locale.ARABIC,"th-th":Locale.THAI,"id-id":Locale.INDONESIAN,"tl":Locale.FILIPINO,
"fil-ph":Locale.FILIPINO,"uk-ua":Locale.UKRAINIAN,"vi-vn":Locale.VIETNAMESE}

@dataclass
class CheckResult:
    rule_id:str; location:Any; input_value:Any=None; system_value:Any=None; message:str|None=None
    def __post_init__(self):
        if isinstance(self.location, str):
            self.location = ObjectLocation.from_model_path(self.location)

class CheckException(Exception):
    """Stable machine-readable model validation failure."""
    def __init__(self, violations):
        self.violations = list(violations)
        super().__init__("Check failed: " + "; ".join(
            result.message or str(result) for result in self.violations
        ))

class I18nCatalog:
    _builtin=None
    def __init__(self, locales:Mapping[str,Any], fallback=None):
        self._locales={Locale.parse(code).value:value for code,value in locales.items()}; self._fallback=fallback
    @classmethod
    def from_dict(cls,value,fallback=None):
        if value.get("schema")!="teaql.i18n/v1": raise ValueError("Unsupported i18n schema")
        return cls(value.get("locales",{}),fallback)
    @classmethod
    def builtin(cls):
        if cls._builtin is None:
            payload=json.loads(files("teaql.runtime").joinpath("builtin-messages-v1.json").read_text("utf-8"))
            cls._builtin=cls.from_dict(payload)
        return cls._builtin
    def _find(self,code,key): return self._locales.get(code,{}).get("messages",{}).get(key)
    def message(self,locale,key):
        return self._find(locale.value,key) or (self._fallback and self._fallback._find(locale.value,key)) or self._find("en",key) or (self._fallback and self._fallback._find("en",key)) or key
    def translate_check_result(self,result,locale):
        rule=getattr(result,"rule_id",getattr(result,"rule","")); rule=getattr(rule,"value",rule)
        keys={"REQUIRED":"checker.required","MIN":"checker.min","MAX":"checker.max","MIN_STR_LEN":"checker.minLength","MIN_LENGTH":"checker.minLength","MAX_STR_LEN":"checker.maxLength","MAX_LENGTH":"checker.maxLength"}
        key=keys.get(str(rule).upper(),f"checker.{str(rule).lower()}")
        input_value=getattr(result,"input_value",getattr(result,"input",None))
        location=getattr(result,"location",None)
        values={"location":location.native_path if isinstance(location,ObjectLocation) else location,"system":getattr(result,"system_value",getattr(result,"system",None)),"input":input_value,"input_len":len(input_value) if hasattr(input_value,"__len__") else 0}
        rendered=self.message(locale,key)
        for name,value in values.items(): rendered=rendered.replace("{"+name+"}",str(value))
        if hasattr(result,"message"): result.message=rendered
        elif hasattr(result,"natural_language_statement"): result.natural_language_statement=rendered
        return result
