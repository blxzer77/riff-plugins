# Add a note

## How to get to it (user POV)

- CLI: `python -m notesapp add "Title" --body "text"`
- API: `POST /notes` with `{"title": ..., "body": ...}`

## Driving it

- `python -m notesapp add "Release checklist" --body "tag and publish"` prints `added #<id>: Release checklist`.
- `curl -fsS "$NOTES_URL/notes"` lists the new note.

## Gotchas

- An empty title is rejected with `error: title is required`.
