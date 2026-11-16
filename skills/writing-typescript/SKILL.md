---
name: writing-typescript
description: "Writes TypeScript the type checker can hold to account. Use when writing or changing TypeScript types: typing JSON or API data, removing any or casts, adding a status or union member, maybe-missing values, look-alike IDs, or porting JavaScript to TypeScript. Not for tests, build or lint setup."
license: Apache-2.0
metadata:
  verified-on: "2026-11-16"
---

# Writing TypeScript

Type errors that reach production usually passed the checker because something told
it to stop looking: an `as`, an `any`, a `!`, a `default` branch that returns a
fallback, a `@ts-ignore`. Write each change so the mistake most likely to follow it
fails to compile, and check at runtime whatever the compiler cannot see.

## Workflow

- [ ] **Read the project's setup first.** Check `tsconfig.json` (`strict`,
      `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `include`), the
      TypeScript version in the lockfile before using newer syntax, and what the
      code already uses: a schema library (zod, valibot, ajv, io-ts), an
      `assertNever` helper, branded ID types. Follow those. Do not change compiler
      options as part of a feature; propose it separately.
- [ ] **Make the change with the rules below.** Ask of each change: what is the next
      mistake here, and will tsc catch it?
- [ ] **Run the type checker and the tests.** Use the project's script or
      `tsc --noEmit`. Running `.ts` files with node, tsx, esbuild or swc strips
      types without checking them, so passing tests say nothing about types.
- [ ] **Prove a compile-time claim before making it.** If you say "this now fails
      to compile", write the wrong code (a swapped call, a new union member),
      show tsc rejecting it, then remove it.
- [ ] **Report** what the compiler now enforces, what is checked at runtime, and
      any escape you had to leave, with the reason.

## Rules

- **Outside data is `unknown` until checked.** `JSON.parse`, `response.json()`,
  environment variables, files, queue messages and `catch` variables carry no
  type. Check the value where it enters and build the typed result from the checked
  parts, naming the field that is wrong. With a schema library, derive the type
  from the schema instead of writing both. `JSON.parse(text) as Config` is not a
  check, and neither is validating and then returning the raw value `as Config`.
- **Make switches over unions exhaustive.** End a `switch` on a discriminant with a
  `default` that assigns the value to `never` (or calls the project's
  `assertNever`), or use a `Record<Union["kind"], …>` lookup. A `default` that
  returns a fallback ("Unknown", `null`, a dot icon) turns the next member into a
  silent wrong answer. When you add a member, remove such fallbacks and let tsc
  list every place that must handle it.
- **One union instead of flags that must agree.** Model states as a discriminated
  union (`{ status: "failed"; error: string } | { status: "done"; url: string }`),
  not as booleans and optional fields that can contradict each other.
- **Put absence in the return type.** A lookup, `find`, `Map.get`, an empty list or
  an index can come back empty: return `T | undefined` and handle it at the caller.
  Do not hide it with `!` or with a value that looks like data (`0`, `""`, `-1`,
  `new Date(0)`). Without `noUncheckedIndexedAccess`, `items[i]` is typed as present
  even when it is not; check it yourself.
- **Stop look-alike arguments from swapping.** When a function takes several values
  of the same type with different meanings (recipient and display name, two IDs,
  cents and dollars), use an object parameter with named fields, or a branded type
  when the value travels far. A brand (`string & { readonly __brand: "Email" }`) is
  created by one function that checks or normalizes the value; that function holds
  the only cast to it.
- **Check literals with `satisfies`, not `as`.** `const routes = {…} satisfies
  Record<string, Route>` checks every entry and keeps the literal types; `as`
  silences missing or misspelled fields (`satisfies` needs TypeScript 4.9 or later).
- **No escapes to make an error go away.** Not `any` (use `unknown` and narrow), not
  `as` to a type the value was never checked against, not `!`, not `@ts-ignore`.
  Narrow with `typeof`, `in`, `instanceof`, `Array.isArray` or a type guard, and a
  guard `(x): x is T` must check everything `T` promises. If a suppression is truly
  needed, use `// @ts-expect-error <reason>`: it fails once the error is gone.
- **Errors from `catch` are `unknown`.** Use `err instanceof Error ? err.message :
  String(err)`, not `(err as Error).message`.

## Gotchas

- `tsc` checks only the files its `include` covers. If tests sit outside it, a
  test that passes the wrong type still runs; it does not prove the API rejects it.
- Defaults moved: TypeScript 6.0 and later default `strict` to `true` and `types`
  to `[]`, so a project without explicit settings can behave differently after an
  upgrade. Read the version and the config rather than assuming.
- An exhaustive `switch` still needs a runtime answer for data from outside: parse
  unknown discriminants at the boundary, so `never` in the switch stays true.
- Lint rules back most of these (typescript-eslint has rules for explicit `any`,
  unsafe assignments, non-null assertions, `@ts-` comments and switch
  exhaustiveness). Use them when the project already has typescript-eslint; adding
  a linter is a separate change.

## References

- `references/sources.md` — the TypeScript and typescript-eslint documentation these rules follow, with versions.
- `assets/agents-snippet.md` — copy into the project's agent instruction file for always-on TypeScript defaults.
