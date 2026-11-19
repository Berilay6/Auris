---
name: note
description: Add, remove or show team decisions in the Auris notes tree (.claude/skills/auris-notes/notes/). Runs only when a user types /note.
argument-hint: "[add|remove|show] <text> (empty: find decisions in this chat)"
disable-model-invocation: true
---

# /note: update the Auris team notes

User input: $ARGUMENTS

The notes live in `.claude/skills/auris-notes/notes/`. The code-path table and
the note format are in `.claude/skills/auris-notes/SKILL.md`. Read that file first.

## Modes

- **Empty input:** read this conversation and list the decisions that teammates
  must know. Leave out personal setup, temporary steps and things that are only
  true for this chat. Ask the user which ones to record, then continue as "add".
- **add <text>:** record this decision.
- **remove <text>:** take this rule out of use.
- **show [area]:** print the matching note. Change nothing.

## add

1. Find the code folder the decision belongs to, using the table in
   `auris-notes/SKILL.md`. If it is not clear, ask the user.
2. Draft two changes:
   - one precise rule in English for the "Rules" section,
   - one row for the "Decision log": today's date, the task key (from the
     branch name, recent commits, or ask the user), the decision, and the
     author's first name (from `git config user.name`, or ask the user).
3. If the decision conflicts with an existing rule, show both and ask which one wins.
4. Show the drafts as a diff and wait for approval. Only then write the file.
   If the note file does not exist yet, create it with the two sections and
   add a row to the table in `auris-notes/SKILL.md`.

## remove

1. Find the matching rule and show it to the user.
2. Ask for a short reason.
3. After approval, delete the rule from "Rules" and add a row to the
   "Decision log": "Removed: <rule> (<reason>)". Never delete log rows.

## After writing

Tell the user which files changed. Do not commit. The note is committed
together with the code of the task.

Offer a short Turkish message the user can paste into the team WhatsApp group.
Do not save that message in the repo.

## Never record

Passwords, tokens, personal data, or anything a user asks to keep private.
