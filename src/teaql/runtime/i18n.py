from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
import builtins
import json
from importlib.resources import files
from typing import Any, Mapping

class JsonFieldNamingProfile(str, Enum):
    CAMEL_CASE = "camelCase"
    SNAKE_CASE = "snake_case"
    PASCAL_CASE = "PascalCase"

    @classmethod
    def parse(cls, value: str | None) -> JsonFieldNamingProfile:
        if value is None or value == "": return cls.CAMEL_CASE
        try: return cls(value)
        except ValueError as error: raise ValueError(f"unsupported json_field_naming: {value}") from error

    def render(self, canonical_name: str) -> str:
        if self is self.SNAKE_CASE: return canonical_name
        camel = _lower_camel(canonical_name)
        return camel if self is self.CAMEL_CASE or not camel else camel[:1].upper() + camel[1:]

@dataclass(frozen=True, eq=False)
class ObjectLocation:
    """A checker location whose source of truth is the canonical KSML path."""
    segments: tuple[tuple[str, Any], ...] = ()

    def property(self, name: str) -> ObjectLocation:
        return ObjectLocation(self.segments + (("property", name),))

    def index(self, value: int) -> ObjectLocation:
        return ObjectLocation(self.segments + (("index", value),))

    def prefixed_by(self, prefix: ObjectLocation) -> ObjectLocation:
        return ObjectLocation(prefix.segments + self.segments)

    @builtins.property
    def model_path(self) -> str:
        return self._render(lambda value: value)

    @builtins.property
    def native_path(self) -> str:
        return self._render(lambda value: value)

    @builtins.property
    def instance_path(self) -> str:
        return self.instance_path_for(JsonFieldNamingProfile.CAMEL_CASE)

    def instance_path_for(self, profile: JsonFieldNamingProfile) -> str:
        parts = []
        for kind, value in self.segments:
            text = str(value) if kind == "index" else profile.render(str(value))
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
    rule_id:str; location:Any; input_value:Any=None; system_value:Any=None; message:str|None=None; entity_type:str|None=None; source_instance_path:str|None=None
    def __post_init__(self):
        if isinstance(self.location, str):
            self.location = ObjectLocation.from_model_path(self.location)
    def prefixed_by(self, prefix: ObjectLocation) -> CheckResult:
        """Add graph location without dropping declaring type or input provenance.

        A submitted source pointer is already boundary-owned and absolute; do
        not reconstruct or rename it when adding canonical graph segments.
        """
        result = replace(self, location=self.location.prefixed_by(prefix))
        if hasattr(self, "_presentation"):
            result._presentation = self._presentation
        if hasattr(self, "_natural_presentation"):
            result._natural_presentation = self._natural_presentation
        return result
    def to_wire(self, profile:JsonFieldNamingProfile=JsonFieldNamingProfile.CAMEL_CASE)->dict[str,Any]:
        from .checker_privacy import project
        safe = project(self)
        return {key:value for key,value in {
            "ruleId":self.rule_id,"entityType":self.entity_type,
            "location":[{"kind":kind, "name":value} if kind=="property" else {"kind":kind,"index":value} for kind,value in self.location.segments],
            "instancePath":self.location.instance_path_for(profile),"sourceInstancePath":self.source_instance_path,
            "inputValue":safe.input_value,"systemValue":safe.system_value,"message":safe.message,
        }.items() if value is not None}

    def __repr__(self):
        return f"CheckResult({self.to_wire()!r})"

class CheckException(Exception):
    """Stable machine-readable model validation failure."""
    def __init__(self, violations):
        from .checker_privacy import project
        self.violations = [project(result) for result in violations]
        # Exception.args must never become a hidden plaintext cache after debug
        # opt-in is revoked. The public formatter reprojects at read time.
        super().__init__("Check failed: " + "; ".join(
            safe.message or repr(safe) for safe in (project(r, force_safe=True) for r in self.violations)))

    def __str__(self):
        return "Check failed: " + "; ".join(result.to_wire().get("message") or repr(result) for result in self.violations)

    def __repr__(self):
        return f"CheckException({str(self)!r})"

    def refresh_presentation(self, violations):
        from .checker_privacy import project
        self.violations = [project(result) for result in violations]
        self.args = ("Check failed: " + "; ".join(
            safe.message or repr(safe) for safe in (project(r, force_safe=True) for r in self.violations)),)

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
    def application_message(self,locale,key):
        return None if self is I18nCatalog.builtin() else self._find(locale.value,key)
    def message(self,locale,key):
        return self._find(locale.value,key) or (self._fallback and self._fallback._find(locale.value,key)) or self._find("en",key) or (self._fallback and self._fallback._find("en",key)) or key
    def translate_check_result(self,result,locale):
        from .checker_privacy import translate
        return translate(self, result, locale)
