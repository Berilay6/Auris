# backend/auris/storage

Code: `backend/auris/storage/` · Architecture decision: HLD MK5

Auris has no database. All persistent data is stored as files under the data
root (`AURIS_DATA_DIR`: `/data` in Docker, `./auris-data` locally).

    base_network/      base network (read-only in the worker container)
    demand/            demand data
    scenarios/<id>/    scenario files
    jobs/<id>/         job data and status
    results/<id>/      simulation output

## Rules

- Get every data path from `auris.storage.layout.DataLayout`. Never join paths
  to the data root by hand. Never read `AURIS_DATA_DIR` directly.
- Store classes take a `DataLayout` in their constructor. Tests pass
  `DataLayout(tmp_path)` and never touch the real data folder.
- Scenario and job ids are lowercase UUID strings made with `str(uuid.uuid4())`.
  Do not add other id formats and do not loosen the id check in `layout.py`.
  Keep human-readable names in a `name` field inside the JSON file.
- Write every file under the data root with `atomic_write_json`,
  `atomic_write_text` or `atomic_write_bytes` from `auris.storage.atomic`.
  Never use `open(path, "w")`, `Path.write_text` or `json.dump` there.
  Reading files in the normal way is fine.
- `DataLayout` only builds paths. It never creates folders.
  `atomic_write_*` creates missing parent folders.
- JSON must not contain NaN or Infinity (`allow_nan=False`). Replace these
  values with `None` before writing.
- `InvalidIdError` is a `ValueError`. Catch it at the API layer and return
  HTTP 400. Return HTTP 404 when the file does not exist.
- When listing data folders, ignore names that start with "." or end with
  ".tmp". These are temporary files of an atomic write.
- `base_network/` is mounted read-only in the worker container. Do not write to it there.
- Do not add database or ORM dependencies.
- Run the tests from `backend/`: `python -m pytest tests/unit/storage`.
  On Windows, 2 skipped tests are expected (symlinks, POSIX file modes).

Example:

    layout = DataLayout.from_env()
    path = layout.job_dir(job_id) / "status.json"
    atomic_write_json(path, {"status": "running"})
    status = json.loads(path.read_text(encoding="utf-8"))

## Decision log

| Date | Task | Decision | Who |
|---|---|---|---|
| 2026-11-19 | SCRUM-11 | Scenario and job ids are lowercase UUIDs | Kaan |
| 2026-11-19 | SCRUM-11 | Data paths come only from `DataLayout` | Kaan |
| 2026-11-19 | SCRUM-11 | Data files are written only with `atomic_write_*` | Kaan |
| 2026-11-19 | SCRUM-11 | No NaN or Infinity in JSON (`allow_nan=False`) | Kaan |
| 2026-11-19 | SCRUM-11 | All result files are stored gzip-compressed (`.gz`) | Kaan |
| 2026-11-19 | SCRUM-11 | Removed: All result files are stored gzip-compressed (test entry, not a real decision) | Kaan |
