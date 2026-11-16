# Sources

The rules follow the TypeScript documentation and typescript-eslint's rule set.
pstack (`cursor/plugins`, MIT) prompted the skill; its TypeScript advice was
rewritten here and checked against the pages below. Fetched and checked on
2026-11-16.

| Source | What this skill takes from it |
|---|---|
| TypeScript Handbook, "Narrowing", section "Exhaustiveness checking" | `default` assigning the value to `never`; adding a member then fails to compile at that switch |
| TypeScript 4.9 release notes, "The `satisfies` Operator" | Checks an expression against a type without changing its type; catches misspelled keys that `as` would hide |
| TypeScript 3.9 release notes, "`// @ts-expect-error` Comments" | Suppresses one error and reports when there is no longer an error to suppress |
| TSConfig reference, `noUncheckedIndexedAccess` | Adds `undefined` to index-signature access; without it, indexed values are typed as present |
| TSConfig reference, `useUnknownInCatchVariables` | `catch` variables are `unknown`; check `instanceof Error` before using one as an Error |
| "Announcing TypeScript 6.0" (Microsoft TypeScript blog, 2026-03-23) | `strict` now defaults to `true`; `types` now defaults to `[]` |
| typescript-eslint rules: `no-explicit-any`, `no-unsafe-assignment`, `no-non-null-assertion`, `ban-ts-comment`, `switch-exhaustiveness-check` | The escapes this skill forbids have lint rules; use them where the project already lints |
| pstack, `cursor/plugins` `bf0c7cd` (MIT; read 2026-11-16) | Prompted the skill: make wrong states unrepresentable, prove compile-time claims with a failing example |

URLs:

- https://www.typescriptlang.org/docs/handbook/2/narrowing.html#exhaustiveness-checking
- https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-9.html
- https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-9.html
- https://www.typescriptlang.org/tsconfig/noUncheckedIndexedAccess.html
- https://www.typescriptlang.org/tsconfig/useUnknownInCatchVariables.html
- https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/
- https://typescript-eslint.io/rules/
- https://github.com/cursor/plugins/tree/main/pstack
