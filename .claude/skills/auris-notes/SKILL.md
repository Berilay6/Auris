---
name: auris-notes
description: Team rules for the Auris codebase, organised like the code tree. Use before writing, changing or reviewing code in this repo (backend, frontend, deploy, data files, AURIS_DATA_DIR, jobs, scenarios, results, ids), and whenever a task leads to a decision that teammates must know.
---

# Auris team notes

Team decisions are stored in `notes/` next to this file, one file per code
folder. The notes are written for AI assistants. Developers share their own
notes outside the repo.

## Before you write code

Find the note for the code you are working on, read its "Rules" section and
follow it. Code that uses another module must also follow that module's note.
For example, API code that writes job files must follow the storage note.

| Code path | Note |
|---|---|
| `backend/auris/storage/` and any file under the data root | `notes/backend/storage.md` |
| `frontend/src/api/` and any backend route the frontend calls | `notes/frontend/api.md` |
| `frontend/src/styles/` | `notes/frontend/styles.md` |

If no note exists for a path, no rules have been recorded for it yet.

## When a task leads to a decision

If the user makes a decision that teammates must know, suggest that they run
`/note` to record it. Do not edit the notes without that command.

## Note format

Each note has two sections:

- **Rules:** short, precise rules in English. Say what to do and what never to do.
- **Decision log:** a table with the columns Date, Task, Decision, Who.
  Rows are never deleted. A removed rule gets a new row that starts with "Removed:".
  Rows are never edited or deleted, even if they are not committed yet. To fix a
  row, add a new row that starts with "Correction:".
