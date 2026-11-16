# Design red flags

Verified on 2026-11-16. Adapted from the sources in `sources.md`.

Check a proposed split, a new interface, or a module that is hard to change against
these. Each is a reason to change the shape, not a point of style.

## The module hides too little

- **Shallow module.** The interface is nearly as large as what it hides. Callers
  chain several calls to do one thing, options expose internal stages, and learning
  the interface saves no one from learning the implementation. Judge depth by how
  much capability sits behind the interface, not by how many layers a call passes
  through.
- **Pass-through method.** A method forwards the same arguments to another method of
  the same shape. Remove the layer, or give it a decision to own: a policy, an
  adaptation, a different abstraction.
- **Information leakage.** One decision (a format, a storage layout, a protocol
  detail) is known in several modules, so changing it means editing all of them.
  Re-exporting wire or storage types is leakage; convert them to the module's own
  types at its edge.
- **Split by time instead of by knowledge.** Separate load, validate, transform, and
  save stages each need the same representation and its rules. Group code by the
  decision it shares; steps that run at different times can live in one module.

## The codebase invites the wrong edit

A contributor, human or agent, often sees only the files they opened, copies the
nearest example, and takes the shortest path that compiles. These shapes turn that
habit into defects:

- **Split ownership.** Two modules write the same state, or each keeps its own copy.
  Whoever edits one writer does not see the other, and their rules drift apart.
  Give the state one owner; others read it or ask the owner to change it.
- **Two ways to do one task.** Whichever way is found first gains another caller, so
  both keep growing. Keep one, move the callers of the other, and delete it in the
  same change.
- **Importable internals.** If importing a module's internals compiles, someone
  will, and they become part of the interface. Make that import fail the build with
  a boundary check.
- **Hand-synced list.** The same items are listed in two places, and adding one
  means editing both. Derive one list from the other, or make the build fail when
  they differ.
