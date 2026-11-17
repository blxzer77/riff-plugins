# Search notes

## How to get to it (user POV)

- CLI: `python -m notesapp search QUERY`
- API: `GET /notes?q=QUERY`

## Driving it

- After adding "Release checklist", `python -m notesapp search release` prints it.
- Search is case-insensitive and matches the body too.
