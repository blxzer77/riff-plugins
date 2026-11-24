# Sources

The behavior this skill changes was measured first: without it, agents asked to add
a case next to existing ones copied the repeated block or the other path's rules in
every run (`docs/EVALUATION_RESULTS.md`, 2026-11-24). The rules follow the sources
below, fetched on 2026-11-24.

| Source | What this skill takes from it |
|---|---|
| Bill Venners, "Orthogonality and the DRY Principle", a conversation with Andy Hunt and Dave Thomas (Artima, 2003) | Every piece of knowledge has one authoritative representation, and DRY is about knowledge, not only code: when one fact in the domain changes, one place in the system changes |
| Martin Fowler, "An example of preparatory refactoring" (2015) | When the code is not shaped for the feature, refactor first and then add it ("make the change easy, then make the easy change", Kent Beck); refactoring keeps behavior and the tests green, separate from adding function |
| Sandi Metz, "The Wrong Abstraction" (2016) | Duplication is cheaper than the wrong abstraction; parameters and conditionals added per caller to shared code show the abstraction is wrong |

URLs:

- https://www.artima.com/articles/orthogonality-and-the-dry-principle
- https://martinfowler.com/articles/preparatory-refactoring-example.html
- https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction
