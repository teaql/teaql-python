from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import json
from importlib.resources import files
from typing import Any, Mapping

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
        values={"location":getattr(result,"location",None),"system":getattr(result,"system_value",getattr(result,"system",None)),"input":input_value,"input_len":len(input_value) if hasattr(input_value,"__len__") else 0}
        rendered=self.message(locale,key)
        for name,value in values.items(): rendered=rendered.replace("{"+name+"}",str(value))
        if hasattr(result,"message"): result.message=rendered
        elif hasattr(result,"natural_language_statement"): result.natural_language_statement=rendered
        return result
