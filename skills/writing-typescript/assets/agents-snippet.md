## TypeScript

- Outside data (JSON, responses, env, files, `catch` errors) is `unknown` until a
  check at the boundary builds the typed value. Never `as` parsed data into a type.
- `switch` over a union ends in a `never` default (or `assertNever`), never in a
  fallback value.
- Return `T | undefined` for values that may be missing; no `!`, no sentinel values.
- Same-typed parameters with different meanings: named-field object or a branded
  type created by one checking function.
- No `any`, `@ts-ignore`, or `as` to silence an error; `@ts-expect-error <reason>`
  only when unavoidable.
- Run the type checker (not just the tests) before reporting done.
