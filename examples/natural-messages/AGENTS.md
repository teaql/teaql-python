# Natural message example

Run `python examples/natural-messages/verify-local.py` against this repository's
local runtime. `fixture/` is generated, read-only implementation. Update its
upstream generator and regenerate it when a model-derived correction is needed;
preserve its manifest and generator provenance. Application assertions belong
in `verify.py`, never in the generated Checkers or presentation metadata.

Use bounded generated Q, loaded E and audited saves. The application must not
install message-model metadata, substitute Checkers or add validation rules to
make this automatic-composition example pass.
