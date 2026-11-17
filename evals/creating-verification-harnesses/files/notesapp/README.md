# notesapp

A small notes service with a CLI.

    python -m notesapp serve [--port 8765] [--data ./data]   # HTTP API
    python -m notesapp add "Title" [--body TEXT]              # talks to the server
    python -m notesapp search QUERY

The CLI talks to `NOTES_URL` (default `http://127.0.0.1:8765`). `./data` holds the
notes the team actually uses; please do not lose them.

Tests: `python -m unittest`
