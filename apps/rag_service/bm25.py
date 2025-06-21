import sqlite_utils, os
DB_PATH = os.getenv("RAG_SQLITE_PATH","bm25.db")
db = sqlite_utils.Database(DB_PATH)
if "fts" not in db.table_names():
    db["fts"].create({
        "point_id": int, 
        "content": str
    }, pk="point_id")
    db["fts"].enable_fts(["content"])

def add_bm25_records(rows):
    db["fts"].insert_all(rows, pk="point_id", replace=True)

def bm25_search(query, k):
    return list(db.query(
        "SELECT point_id, bm25(fts) AS score, snippet(fts,0,'>','<','…',10) AS snip "
        "FROM fts WHERE fts MATCH ? ORDER BY score LIMIT ?", (query, k)))