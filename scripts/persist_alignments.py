"""Enhanced persistence of alignments with metadata, validation and indexes.

This script reads the canonical CSV (default: res/stanza_word_matches_0005_greedy_vs_dp.csv)
and writes three artifacts with a configurable prefix (default: res/alignments_0005):

- {prefix}.db      (SQLite) with strict schema, constraints and indexes
- {prefix}.jsonl   (newline-delimited JSON)
- {prefix}.meta.json  (metadata: source sha256, row count, thresholds, git commit)

It also prints validation statistics and a small per-witness/stanza summary.
"""

import argparse
import csv
import json
import os
import sqlite3
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, List

DEFAULT_CSV = "res/stanza_word_matches_0005_greedy_vs_dp.csv"
DEFAULT_PREFIX = "res/alignments_0005"


def normalize_indexes(text: str) -> List[Any]:
    if text is None:
        return []
    text = str(text).strip()
    if text == "":
        return []
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    if not text:
        return []
    parts = [p.strip() for p in text.replace(';', ',').split(',') if p.strip()]
    out = []
    for p in parts:
        try:
            out.append(int(p))
        except Exception:
            out.append(p)
    # dedupe while preserving order
    seen = set()
    dedup = []
    for v in out:
        if v not in seen:
            seen.add(v)
            dedup.append(v)
    return dedup


def decide_final(greedy: Dict[str, Any], dp: Dict[str, Any]) -> Dict[str, Any]:
    # Prefer DP when dp_relation exists and is not blank; otherwise greedy; if both equal, chosen='both'
    grel = (greedy.get("greedy_relation") or "").strip()
    drel = (dp.get("dp_relation") or "").strip()
    if drel:
        if drel != grel:
            return {
                "chosen": "dp",
                "relation": drel,
                "canon_indexes": normalize_indexes(dp.get("dp_canon_indexes", "")),
                "canon_words": dp.get("dp_canon_words"),
                "confidence": None,
            }
        else:
            return {
                "chosen": "both",
                "relation": drel,
                "canon_indexes": normalize_indexes(dp.get("dp_canon_indexes", "")),
                "canon_words": dp.get("dp_canon_words"),
                "confidence": None,
            }
    if grel:
        return {
            "chosen": "greedy",
            "relation": grel,
            "canon_indexes": normalize_indexes(greedy.get("greedy_canon_indexes", "")),
            "canon_words": greedy.get("greedy_canon_words"),
            "confidence": None,
        }
    return {"chosen": "none", "relation": None, "canon_indexes": [], "canon_words": None, "confidence": None}


def create_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    # If the table does not exist, create it. If it exists but is older, add missing columns.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alignments'")
    exists = cur.fetchone() is not None
    if not exists:
        cur.execute(
            """
            CREATE TABLE alignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                witness_id TEXT NOT NULL,
                stanza_id TEXT,
                our_index INTEGER NOT NULL,
                our_word_raw TEXT NOT NULL,
                our_word_norm TEXT,

                greedy_relation TEXT,
                greedy_canon_indexes TEXT NOT NULL,
                greedy_canon_words TEXT,
                greedy_group_canon_words TEXT,

                dp_relation TEXT,
                dp_canon_indexes TEXT NOT NULL,
                dp_canon_words TEXT,
                dp_group_canon_words TEXT,

                final_choice TEXT NOT NULL CHECK(final_choice IN ('dp','greedy','both','none')),
                final_relation TEXT,
                final_canon_indexes TEXT NOT NULL,
                final_canon_words TEXT,
                final_confidence REAL,

                raw_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(witness_id, stanza_id, our_index)
            )
            """
        )
        conn.commit()
    else:
        # migration: ensure necessary columns exist, add if missing
        cur.execute("PRAGMA table_info(alignments)")
        existing = {row[1] for row in cur.fetchall()}  # name is at index 1
        wanted = {
            'witness_id': "TEXT",
            'stanza_id': "TEXT",
            'our_index': "INTEGER",
            'our_word_raw': "TEXT",
            'our_word_norm': "TEXT",
            'greedy_relation': "TEXT",
            'greedy_canon_indexes': "TEXT",
            'greedy_canon_words': "TEXT",
            'greedy_group_canon_words': "TEXT",
            'dp_relation': "TEXT",
            'dp_canon_indexes': "TEXT",
            'dp_canon_words': "TEXT",
            'dp_group_canon_words': "TEXT",
            'final_choice': "TEXT",
            'final_relation': "TEXT",
            'final_canon_indexes': "TEXT",
            'final_canon_words': "TEXT",
            'final_confidence': "REAL",
            'raw_json': "TEXT",
        }
        for col, coltype in wanted.items():
            if col not in existing:
                # add the column with NULL default
                cur.execute(f"ALTER TABLE alignments ADD COLUMN {col} {coltype}")
        conn.commit()

    # Indexes for common queries (create after ensuring columns exist)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_align_stanza_witness_idx ON alignments (stanza_id, witness_id, our_index)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_align_stanza ON alignments (stanza_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_align_final ON alignments (final_choice, final_relation)")
    conn.commit()


def persist_row(conn: sqlite3.Connection, row: Dict[str, Any], raw_json: str):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO alignments (
            witness_id, stanza_id, our_index, our_word_raw, our_word_norm,
            greedy_relation, greedy_canon_indexes, greedy_canon_words, greedy_group_canon_words,
            dp_relation, dp_canon_indexes, dp_canon_words, dp_group_canon_words,
            final_choice, final_relation, final_canon_indexes, final_canon_words, final_confidence,
            raw_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            row.get("witness_id"),
            row.get("stanza_id"),
            int(row.get("our_index")) if row.get("our_index") not in (None, "") else None,
            row.get("our_word_raw"),
            row.get("our_word_norm"),
            row.get("greedy_relation"),
            json.dumps(normalize_indexes(row.get("greedy_canon_indexes", "")), ensure_ascii=False),
            row.get("greedy_canon_words"),
            row.get("greedy_group_canon_words"),
            row.get("dp_relation"),
            json.dumps(normalize_indexes(row.get("dp_canon_indexes", "")), ensure_ascii=False),
            row.get("dp_canon_words"),
            row.get("dp_group_canon_words"),
            row.get("final_choice"),
            row.get("final_relation"),
            json.dumps(row.get("final_canon_indexes") or [], ensure_ascii=False),
            row.get("final_canon_words"),
            row.get("final_confidence"),
            raw_json,
        ),
    )
    conn.commit()


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=DEFAULT_CSV)
    parser.add_argument("--out-prefix", default=DEFAULT_PREFIX,
                        help="Prefix for outputs: {prefix}.db/.jsonl/.meta.json")
    parser.add_argument("--pair-threshold", type=float, default=0.9,
                        help="Pair extraction threshold used when auto-pairing inside DP groups (informational)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing DB and outputs")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"CSV not found: {args.csv}")
        return

    db_path = args.out_prefix + ".db"
    jsonl_path = args.out_prefix + ".jsonl"
    meta_path = args.out_prefix + ".meta.json"

    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
    if args.force and os.path.exists(db_path):
        os.remove(db_path)
        if os.path.exists(jsonl_path):
            os.remove(jsonl_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)

    conn = sqlite3.connect(db_path)
    create_db(conn)

    total = 0
    with open(args.csv, newline="", encoding="utf-8") as fh, open(jsonl_path, "w", encoding="utf-8") as out_f:
        reader = csv.DictReader(fh)
        for r in reader:
            total += 1
            # Map columns to stable names
            xml_id = (r.get("xml_id") or r.get("xml") or r.get("witness_id") or "").strip()
            # xml_id often encodes stanza like Y1.1; if so, we keep it in stanza_id and witness prefix as witness_id
            witness_part = None
            stanza_part = None
            if xml_id:
                if "." in xml_id:
                    witness_part, stanza_part = xml_id.split('.', 1)
                    # normalize witness to include prefix if not present
                    witness_part = witness_part.strip()
                    stanza_part = xml_id  # keep full label as stanza_id (e.g., Y1.1)
                else:
                    witness_part = xml_id
                    stanza_part = None

            row = {
                "witness_id": witness_part,
                "stanza_id": stanza_part,
                "our_index": r.get("our_index") or r.get("our_idx") or r.get("our"),
                "our_word_raw": r.get("our_word") or r.get("our_token") or r.get("our"),
                "our_word_norm": r.get("our_word_norm") or r.get("our_word_cleaned") or None,

                "greedy_relation": r.get("greedy_relation"),
                "greedy_canon_indexes": r.get("greedy_canon_indexes"),
                "greedy_canon_words": r.get("greedy_canon_words"),
                "greedy_group_canon_words": r.get("greedy_group_canon_words"),

                "dp_relation": r.get("dp_relation"),
                "dp_canon_indexes": r.get("dp_canon_indexes"),
                "dp_canon_words": r.get("dp_canon_words"),
                "dp_group_canon_words": r.get("dp_group_canon_words"),
            }

            greedy = {
                "greedy_relation": row.get("greedy_relation"),
                "greedy_canon_indexes": row.get("greedy_canon_indexes"),
                "greedy_canon_words": row.get("greedy_canon_words"),
            }
            dp = {
                "dp_relation": row.get("dp_relation"),
                "dp_canon_indexes": row.get("dp_canon_indexes"),
                "dp_canon_words": row.get("dp_canon_words"),
            }
            final = decide_final(greedy, dp)
            row["final_choice"] = final.get("chosen")
            row["final_relation"] = final.get("relation")
            row["final_canon_indexes"] = final.get("canon_indexes")
            row["final_canon_words"] = final.get("canon_words")
            row["final_confidence"] = final.get("confidence")

            raw_json = json.dumps(r, ensure_ascii=False)
            # Write JSONL row (stable field names)
            out_row = {
                "witness_id": row.get("witness_id"),
                "stanza_id": row.get("stanza_id"),
                "our_index": row.get("our_index"),
                "our_word_raw": row.get("our_word_raw"),
                "our_word_norm": row.get("our_word_norm"),
                "greedy_relation": row.get("greedy_relation"),
                "greedy_canon_indexes": normalize_indexes(row.get("greedy_canon_indexes")),
                "greedy_canon_words": row.get("greedy_canon_words"),
                "greedy_group_canon_words": row.get("greedy_group_canon_words"),
                "dp_relation": row.get("dp_relation"),
                "dp_canon_indexes": normalize_indexes(row.get("dp_canon_indexes")),
                "dp_canon_words": row.get("dp_canon_words"),
                "dp_group_canon_words": row.get("dp_group_canon_words"),
                "final_choice": row.get("final_choice"),
                "final_relation": row.get("final_relation"),
                "final_canon_indexes": row.get("final_canon_indexes") or [],
                "final_canon_words": row.get("final_canon_words"),
                "final_confidence": row.get("final_confidence"),
            }
            out_f.write(json.dumps(out_row, ensure_ascii=False) + "\n")
            # Ensure required fields
            if not out_row.get("witness_id") or out_row.get("our_index") in (None, ""):
                # skip and warn
                print(f"Skipping row due to missing witness_id or our_index: {out_row}")
                continue
            # ensure non-null our_word_raw
            if out_row.get("our_word_raw") is None:
                out_row["our_word_raw"] = ""
            persist_row(conn, out_row, raw_json)

    conn.close()

    # Write metadata
    meta = {
        "source_csv": os.path.abspath(args.csv),
        "source_sha256": sha256_of_file(args.csv),
        "row_count": total,
        "created_at": datetime.utcnow().isoformat() + 'Z',
        "pair_threshold": args.pair_threshold,
        "script": os.path.abspath(__file__),
    }
    # try to add git commit if available
    try:
        import subprocess
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        meta["git_commit"] = commit
    except Exception:
        meta["git_commit"] = None

    with open(meta_path, "w", encoding="utf-8") as mf:
        json.dump(meta, mf, ensure_ascii=False, indent=2)

    # Validation checks
    print(f"Wrote {total} rows to {db_path} and {jsonl_path}")
    print("Metadata:")
    print(json.dumps(meta, indent=2))

    # Basic sanity and coverage reports
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM alignments")
    db_count = cur.fetchone()[0]
    print(f"DB rows: {db_count}")
    if db_count != total:
        print("WARNING: DB row count differs from CSV rows")

    # coverage stats
    cur.execute("SELECT COUNT(*) FROM alignments WHERE final_choice!='none'")
    with_choice = cur.fetchone()[0]
    print(f"Rows with final.choice set: {with_choice} ({with_choice/total:.1%})")

    # disagreements: greedy != dp
    cur.execute("SELECT COUNT(*) FROM alignments WHERE (greedy_relation IS NOT NULL AND dp_relation IS NOT NULL AND greedy_relation!=dp_relation)")
    disagreements = cur.fetchone()[0]
    print(f"Greedy vs DP disagreements: {disagreements} ({disagreements/total:.1%})")

    # unmatched
    cur.execute("SELECT COUNT(*) FROM alignments WHERE final_relation='unmatched'")
    unmatched = cur.fetchone()[0]
    print(f"Final unmatched rows: {unmatched} ({unmatched/total:.1%})")

    # spot checks: print first 3 rows
    cur.execute("SELECT witness_id, stanza_id, our_index, our_word_raw, greedy_relation, dp_relation, final_choice FROM alignments ORDER BY id ASC LIMIT 3")
    print("Spot checks (first 3 rows):")
    for r in cur.fetchall():
        print(r)

    # summary counts by final_relation per witness (top 10)
    cur.execute("SELECT witness_id, final_relation, COUNT(*) FROM alignments GROUP BY witness_id, final_relation ORDER BY witness_id LIMIT 50")
    print("Counts by witness and final_relation (sample):")
    for row in cur.fetchall():
        print(row)

    conn.close()


if __name__ == "__main__":
    main()
