import subprocess, pathlib, itertools, hashlib, re, json
from .embedding import embed
from .vector import upsert_vectors
from .bm25 import add_bm25_records

TOKEN_SPLIT = re.compile(r"\n{2,}")

def file_chunks(path, text):
    for i, block in enumerate(TOKEN_SPLIT.split(text)):
        if block.strip():
            point_id = int(hashlib.md5(f"{path}:{i}".encode()).hexdigest()[:16],16)
            yield point_id, block

def ingest_git_commit(commit_sha, repo_dir):
    changed = subprocess.check_output(
        ["git","diff-tree","--no-commit-id","--name-only","-r",commit_sha],
        cwd=repo_dir, text=True).splitlines()
    for fp in changed:
        full = pathlib.Path(repo_dir)/fp
        if not full.exists(): continue
        txt = full.read_text(encoding="utf-8", errors="ignore")
        rows, payloads, vecs = [], [], []
        for pid, chunk in file_chunks(fp, txt):
            rows.append({"point_id": pid, "content": chunk})
            payloads.append({"path": fp})
            vecs.append(chunk)
        if rows:
            add_bm25_records(rows)
            upsert_vectors([r["point_id"] for r in rows], embed(vecs), payloads)