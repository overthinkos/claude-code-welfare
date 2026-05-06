# Jupyter MCP — Root Cause Analysis: silent notebook corruption from `cell_update` + persistent rooms

**Status**: bug report / RCA, addressed to maintainers of `jupyter-mcp-server` and `jupyter-server-ydoc` / `jupyter_collaboration`.

**Symptoms reproduced**: silent cell duplication and silent code-cell loss when calling `mcp__jupyter__cell_update` against a notebook whose CRDT room is stale. Subsequent recovery via `git checkout` + direct disk write further corrupts disk via CRDT merge.

**Repro environment**:
- `jupyter-lab` 3.13 (pixi env), `jupyter_server_ydoc` (CRDT/RTC backend)
- Two `jupyter-lab` processes on port 8888 — one host (`atrawog` uid 1000), one container (`ov-jupyter`, uid 100999). The host one served this session.
- 10 notebooks in `claude-prompts-analysis/` were edited; 3 of them (`00_`, `10_`, `20_`) had previously been opened via `mcp__jupyter__room_open` during the session.

---

## 1. Reproduction — what happened

### 1.1 Initial cell_update via MCP corrupts the room

After `room_open(20_track_justification_rate.ipynb)` (a 14-cell notebook), I called:

```
cell_update(index=0,  cell_type="markdown", source=NEW_CELL_0)
cell_update(index=11, cell_type="markdown", source=NEW_CONCLUSIONS)
cell_update(index=12, cell_type="markdown", source=NEW_RECOMMENDATIONS)
cell_update(index=13, cell_type="markdown", source=NEW_LIMITATIONS)
cell_update(index=8,  cell_type="markdown", source=NEW_CELL_8)
cell_update(index=10, cell_type="markdown", source=NEW_CELL_10)
cell_update(index=6,  cell_type="markdown", source=NEW_CELL_6)
```

Server returned `Cell N updated` for each. Then `notebook_get` showed **15 cells** with two cells starting `# Idea 1 — ...` and `# Track justification rate ...` (the old and new cell-0 content), AND two cells starting with `## 3. Per-file dashboard` (old and new cell-6). Two **code cells** that originally rendered charts (the cumulative-trend chart at index 5 and the per-category breakdown at index 9) were **missing entirely** — silently deleted.

Cell-count delta: +1 cell per `cell_update` after the first, with code-cell loss compensating partially. Net pattern: each `cell_update` appears to perform `delete-then-insert` rather than in-place replacement, but the delete and insert target *different* cells in the CRDT log, leaving the original behind and causing the new one to land elsewhere.

### 1.2 `room_close_all` saves the corrupted state to disk

After observing the corruption, I called `room_close_all`. Server returned `closed: [...]` for the relevant rooms. Disk now contained the 15-cell corrupted state.

### 1.3 `git checkout` restores disk but does NOT restore the room

`git checkout HEAD -- 20_*.ipynb` restored disk to 14 cells (clean). However:

```bash
$ mcp__jupyter__room_list
{
  "result": [
    {"path": "20_track_justification_rate.ipynb", "file_id": "aabcdcef-...", ...},
    ...
  ]
}
```

The room **persisted** (same `file_id` from before close). Multiple subsequent `room_close_all` calls did not destroy this room.

### 1.4 Direct disk-edit triggers CRDT merge → re-corruption

A Python script that read 20_*.ipynb (14 cells), updated `cells[i].source` for 7 indices, and wrote back via `path.write_text()` produced — on disk — a **21-cell** notebook with duplicate copies of edited cells.

This is consistent with `jupyter_server_ydoc`'s file-watcher detecting an external modification, loading the disk's 14 cells, and computing a yjs CRDT merge against the persistent room's stale state. Cell IDs from my script (inherited from the original `git checkout` content) would not match the room's IDs (which had been replaced by `cell_update`'s delete-then-insert), so the merge would yield 14 disk cells + 7 room-only cells = 21 cells.

### 1.5 Control case — fresh room cleanly destroyed

`mcp__jupyter__room_open(13_correlation_directiveness.ipynb)` followed immediately by `room_close(...)` succeeded in destroying the room — `room_list` no longer included it.

The asymmetry: rooms with **clean CRDT state** can be destroyed; rooms with **dirty / divergent CRDT state** become "sticky" and outlive `room_close`.

---

## 2. Root cause hypotheses

### 2.1 `cell_update` is not atomic

In `jupyter-mcp-server`'s implementation of `cell_update`, the operation against a `Y.Array` of cells is presumably:

```python
y_cells.delete(index, 1)
y_cells.insert(index, [new_cell])
```

In a single-client room with no concurrent operations, this is fine. But:

- If the room's `Y.Doc` has any concurrent operation in flight (from a kernel writing outputs, from a now-disconnected JupyterLab UI client whose ops haven't been GCed, from an earlier failed `cell_update` that left an in-doc tombstone), yjs's deterministic merge ordering may apply the `delete(index, 1)` to a cell different from what the caller intended.

- The yjs delete-by-index targets the cell at a specific *position-in-array-order-after-merge*, which depends on causal history. If the room's causal history has cells the MCP client doesn't know about, the index resolves differently than expected.

- The result: insert lands at the right position, but the delete doesn't remove what the user wants removed.

**Proposed fix**: target cells by `cell_id` (the stable per-cell GUID), not by index. The `Y.Map` for each cell has an `id` field. `cell_update` should:

```python
for i, cell in enumerate(y_cells):
    if cell["id"] == target_id:
        y_cells.delete(i, 1)
        y_cells.insert(i, [new_cell_with_same_id])
        return
```

…or, even better, update the cell's `source` field in-place (a `Y.Text` mutation) without the delete/insert dance, preserving the cell's identity entirely.

### 2.2 `room_close` does not actually destroy dirty rooms

The MCP server's `room_close` returns `Room closed for ...`, suggesting success. But `room_list` still lists the room. This indicates one of:

- The MCP server's close handler only marks the room as "should close" and relies on `jupyter_server_ydoc` to do the actual cleanup, which it doesn't do for rooms with unsaved CRDT state (rooms in dirty state are kept alive until next save flush, indefinitely if no save trigger fires).

- `room_close` flushes to disk and disconnects MCP's client but leaves the in-memory `Y.Doc` for other consumers (file watchers, future opens). The same `file_id` keeps the room reachable.

**Proposed fix**: `room_close` should force a hard destroy:

1. Flush to disk (current behavior).
2. Disconnect all clients.
3. **Delete the `Y.Doc` and the room registry entry**, so `room_list` no longer returns it and the next access loads fresh from disk.

A `room_close(force=True)` parameter would be the minimally invasive option.

### 2.3 Disk-modification detection re-instantiates rooms with merge semantics

When `jupyter_server_ydoc`'s file watcher detects an external `.ipynb` mutation (e.g., my Python script's `write_text`), it triggers a "reload from disk" in the room. The reload behavior appears to be:

1. Parse the new disk content into a candidate cell list.
2. Construct a new `Y.Doc` representing the disk content.
3. **CRDT-merge** that with the existing room's `Y.Doc`.

Step 3 is the failure mode: if the existing room state is divergent from disk (because of prior MCP `cell_update` calls), the merge produces hybrid output containing both versions of every modified cell.

**Proposed fix**: when an external file modification is detected for a room, the contents manager / RTC extension should:

- Ask the room "is your state dirty or clean (matches last known disk write)?"
- If clean → reload from disk wholesale (replace the `Y.Doc`).
- If dirty → **fail the load with a visible warning** rather than silently merging. Display "external edit conflicts with in-memory state; reject one of them" and let the user choose. Silent CRDT merging on JSON-document-level changes is the wrong default for notebooks.

### 2.4 No safety rail in MCP `cell_update` against detectable corruption

After `cell_update`, the MCP server could trivially read back the cell at the target index and verify the source matches what was sent. If it doesn't match → the operation failed and should return an error rather than `Cell N updated`.

**Proposed fix**: add a post-write read-and-verify in `cell_update`. Latency cost: one extra round trip. Correctness benefit: silent corruption becomes loud failure.

---

## 3. Concrete reproducer for the maintainer

### 3.1 Reproduce cell duplication

```bash
# In a fresh JupyterLab+jupyter_server_ydoc+jupyter_mcp_server environment:
# 1. Have a notebook with N cells on disk (any notebook).
# 2. Open via MCP:
mcp__jupyter__room_open(path="notebook.ipynb")
# 3. Make several cell_update calls in sequence:
mcp__jupyter__cell_update(path="notebook.ipynb", index=0, cell_type="markdown", source="new0")
mcp__jupyter__cell_update(path="notebook.ipynb", index=1, cell_type="markdown", source="new1")
mcp__jupyter__cell_update(path="notebook.ipynb", index=2, cell_type="markdown", source="new2")
# 4. Inspect:
mcp__jupyter__notebook_get(path="notebook.ipynb")
# Expected: N cells with cells 0/1/2 source updated.
# Observed in this session: N+k cells with duplicate copies of edited cells.
```

The bug may not always reproduce — it depends on whether the room has any concurrent yjs operations in flight. Triggering it more reliably probably needs:

- A long-lived room (opened minutes ago, with cell IDs persisted in the file_id_manager).
- Mixed read + write operations interleaved.
- Possibly multiple `room_open` + `room_close` cycles on the same path.

### 3.2 Reproduce sticky room after close

```bash
mcp__jupyter__room_open(path="notebook.ipynb")
mcp__jupyter__cell_update(path="notebook.ipynb", index=0, cell_type="markdown", source="new0")
mcp__jupyter__room_close(path="notebook.ipynb")
mcp__jupyter__room_list
# Expected: room not in list.
# Observed in this session: room still listed (file_id persists).
```

### 3.3 Reproduce CRDT-merge-on-disk-modify

```bash
# Pre-state: notebook room is "sticky" (per 3.2)
# Direct edit on disk:
echo "$NEW_CONTENT" > notebook.ipynb   # or any tool that doesn't go through Jupyter
# Wait briefly for file watcher
mcp__jupyter__notebook_get(path="notebook.ipynb")
# Expected: my new content.
# Observed: merged content (cells from my edit + cells from sticky room).
```

---

## 4. Diagnostic data to capture (for the maintainer)

When this issue is reported in the wild, useful state to capture:

1. **`mcp__jupyter__room_list` output** before/after — shows whether the room is sticky.
2. **`Y.Doc.encodeStateVector()` of the room** at the moment of the bad merge — shows the causal history.
3. **The `file_id`** for the affected notebook from `jupyter_server_fileid`'s database (`<user>/.local/share/jupyter/runtime/file_id_manager.db` or similar) — shows whether the file_id is being reused.
4. **`stat -c '%Y' notebook.ipynb`** before and after MCP operations — shows whether the room's writeback fired after disk edits.
5. **Any browser tabs** the user has open against the same notebook — even tabs with no active focus can hold WebSocket connections that prevent room cleanup.

---

## 5. Workarounds for users (until fixed)

1. **Never mix MCP `cell_update` with direct disk writes on the same notebook in one session.** Pick one and commit.

2. **For bulk edits, prefer direct disk writes** over many `cell_update` calls. If you must use MCP, do it one-cell-at-a-time with a `notebook_get` verification between each call.

3. **After any suspected corruption**:
   - `room_close_all` (just in case).
   - `git checkout` to restore disk.
   - **Restart the Jupyter server process** (this is the only certain way to flush all in-memory rooms).
   - Re-open notebooks fresh from disk.

4. **Always verify cell counts** after every batch of `cell_update` calls. If count grew, stop immediately and recover.

5. **Targeting cells by content rather than index** is more robust: search for the cell with a known opening line, then update *that* cell. (Not currently exposed by the MCP API, but easy to implement client-side.)

---

## 6. Questions the maintainer probably has to answer to design a real fix

- Should `cell_update` be guaranteed atomic in single-writer scenarios (the most common case)? If yes, the implementation needs to use yjs's `Y.Map.set("source", ...)` rather than delete-then-insert at the cell-array level.
- Should `room_close` always destroy the room, or should there be a `room_close(force=True)` parameter? What's the right default?
- When file-watcher detects external modification, is silent CRDT merging ever correct for notebook JSON, or should it always reject + surface a conflict?
- Should `room_open` against a sticky room return an error, refresh-from-disk, or preserve the existing CRDT state? Currently the user can't tell which it does.

---

*This RCA was prepared during a Claude Code session, 2026-05-06, after debugging silent corruption of `claude-prompts-analysis/20_track_justification_rate.ipynb`. The notebook was recovered to a known-good state via `git checkout` + careful disk-edit + cell-count verification. The full session transcript is available on request.*
