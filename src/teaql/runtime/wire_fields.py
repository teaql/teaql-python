from __future__ import annotations
from dataclasses import dataclass
from types import MappingProxyType
from .i18n import CheckResult, JsonFieldNamingProfile

@dataclass(frozen=True)
class WireFieldMetadata:
    canonical_name: str
    wire_name: str
    aliases: tuple[str, ...] = ()

@dataclass(frozen=True)
class WireEntityMetadata:
    entity_type: str
    profile: JsonFieldNamingProfile
    fields: object

@dataclass(frozen=True)
class NormalizedWireInput:
    values: object
    source_instance_paths: object

class WireInputError(ValueError):
    def __init__(self, code, instance_path, message):
        super().__init__(message); self.code = code; self.instance_path = instance_path

def create_wire_entity_metadata(entity_type, canonical_fields, profile=JsonFieldNamingProfile.CAMEL_CASE, aliases=None):
    aliases = aliases or {}; fields = {}; spellings = {}
    for canonical_name in canonical_fields:
        field = WireFieldMetadata(canonical_name, profile.render(canonical_name), tuple(aliases.get(canonical_name, ())))
        for spelling in (field.wire_name, *field.aliases):
            previous = spellings.get(spelling)
            if previous is not None and previous != canonical_name:
                raise ValueError(f"Wire field spelling '{spelling}' maps to both '{previous}' and '{canonical_name}'")
            spellings[spelling] = canonical_name
        fields[canonical_name] = field
    return WireEntityMetadata(entity_type, profile, MappingProxyType(fields))

def normalize_wire_input(input_value, metadata, parent_pointer=""):
    lookup = {spelling: field for field in metadata.fields.values() for spelling in (field.wire_name, *field.aliases)}
    values = {}; paths = {}; submitted = {}
    for submitted_name, value in input_value.items():
        pointer = f"{parent_pointer}/{_escape_pointer(submitted_name)}"; field = lookup.get(submitted_name)
        if field is None: raise WireInputError("WIRE_UNKNOWN_FIELD", pointer, f"Unknown {metadata.entity_type} field '{submitted_name}'")
        previous = submitted.get(field.canonical_name)
        if previous is not None: raise WireInputError("WIRE_FIELD_COLLISION", pointer, f"Fields '{previous}' and '{submitted_name}' both map to canonical field '{field.canonical_name}'")
        submitted[field.canonical_name] = submitted_name; values[field.canonical_name] = value
        if submitted_name != field.wire_name: paths[field.canonical_name] = pointer
    return NormalizedWireInput(MappingProxyType(values), MappingProxyType(paths))

def encode_wire_output(values, metadata):
    output = {}
    for canonical_name, value in values.items():
        field = metadata.fields.get(canonical_name)
        if field is None: raise ValueError(f"Unknown canonical {metadata.entity_type} field '{canonical_name}'")
        output[field.wire_name] = value
    return MappingProxyType(output)

def retain_submitted_paths(results, normalized):
    retained = []
    for result in results:
        canonical = next((value for kind, value in result.location.segments if kind == "property"), None)
        retained.append(CheckResult(result.rule_id, result.location, result.input_value, result.system_value, result.message, result.entity_type, normalized.source_instance_paths.get(canonical, result.source_instance_path)))
    return retained

def _escape_pointer(value): return value.replace("~", "~0").replace("/", "~1")
