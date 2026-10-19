# Changelog

## 1.2.1 - 2026-10-19

- Validate configured requirement shapes before missing-field or hypothetical omission shortcuts. Keep all operator, matrix and missing-policy semantics for valid inputs.
- Keep authored labels and IDs literal in Markdown without changing JSON evidence.
- Create reports exclusively, refuse symlink destinations and handle closed output pipes with a clean error.
- Include handoff documents, license and the supplied example in both release package formats.

## 1.2.0 - 2026-10-15

- Compare explicit hypothetical constraint omissions while retaining the original complete matrix and missing-field policy.
- Report only affected eligibility transitions without ranking options. Reject unknown or repeated omission IDs and ambiguous constraint IDs.

## 1.1.0 - 2026-07-27

- Added a complete option-versus-constraint matrix with pass, fail, ignored, and unknown states.
- Added configurable `fail`, `ignore`, and `unknown` policies for missing fields.
- Added a separate unknown classification so incomplete options do not have to be eliminated.

## 1.0.0 - 2026-07-26

- Added structured options, attributes, and hard constraints.
- Added eight explicit comparison operators with type validation.
- Added surviving and eliminated reports with exact failure evidence.
