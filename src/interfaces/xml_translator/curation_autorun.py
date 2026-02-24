import os
import sys
import time
import csv
import threading
import subprocess
from collections import deque
from datetime import datetime
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except Exception as e:
    print("watchdog is required. Install with: pip install watchdog", file=sys.stderr)
    raise

WATCH_FILE = Path('res/Yasna/meta/unknown_review_for_curator.csv').resolve()
WATCH_DIR = WATCH_FILE.parent

# Commands to run
PY_EXE = sys.executable or 'python'
OVERRIDES_CMD = [
    PY_EXE,
    'src/interfaces/xml_translator/build_overrides_from_curation.py',
    '--curator-in', str(WATCH_FILE),
    '--out-features', 'res/Yasna/meta/label_overrides_features.csv',
    '--out-readings', 'res/Yasna/meta/label_overrides_readings.csv',
]
ANNOTATE_CMD = [
    PY_EXE,
    'src/interfaces/xml_translator/tei_annotate_v3_direct.py',
    '--tei', 'res/Yasna/apparatus/multi',
    '--features', 'res/Yasna/meta/feature_scored.csv',
    '--label-changes', 'res/Yasna/meta/feature_label_changes.csv',
    '--orthography-families', 'res/Yasna/meta/orthography_families_v3.yaml',
    '--lexical-whitelist', 'res/Yasna/meta/lexical_whitelist_v3.txt',
    '--overrides-features', 'res/Yasna/meta/label_overrides_features.csv',
    '--overrides-readings', 'res/Yasna/meta/label_overrides_readings.csv',
    '--unknown-out', 'res/Yasna/meta/unknown_review_after_overrides.csv',
    '--aggressive-infer',
]
SUMMARY_CMD = [
    PY_EXE,
    'src/interfaces/xml_translator/tei_annotation_summary.py',
    '--tei', 'res/Yasna/apparatus/multi'
]

UNKNOWN_OUT = Path('res/Yasna/meta/unknown_review_after_overrides.csv')

# Debounce interval in seconds
DEBOUNCE_SECONDS = 1.0

# Keep the last 10 actions
ACTION_LOG = deque(maxlen=10)

def ts() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def log_action(message: str) -> None:
    entry = f"[{ts()}] {message}"
    ACTION_LOG.append(entry)
    print(entry, flush=True)


def count_unknowns(csv_path: Path) -> int:
    if not csv_path.exists():
        return 0
    try:
        with csv_path.open('r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # subtract header if present
            return max(0, sum(1 for _ in reader) - 1)
    except Exception:
        return 0


def run_cmd(cmd, label: str) -> tuple[int, str, str]:
    log_action(f"Running {label}: {' '.join(cmd)}")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        log_action(f"{label} failed with code {proc.returncode}")
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
    else:
        # Print a shortened stdout (first few lines) for context
        out_lines = (proc.stdout or '').strip().splitlines()
        if out_lines:
            preview = '\n'.join(out_lines[:5])
            print(preview, flush=True)
        log_action(f"{label} finished: exit {proc.returncode}")
    return proc.returncode, proc.stdout, proc.stderr


def pipeline_run():
    start = time.time()
    log_action("Starting pipeline run…")

    # 1) Build overrides from curation
    rc1, out1, err1 = run_cmd(OVERRIDES_CMD, 'build_overrides_from_curation')

    # 2) Re-annotate with aggressive inference + overrides
    rc2, out2, err2 = run_cmd(ANNOTATE_CMD, 'tei_annotate_v3_direct')

    # 3) Print unknowns count
    unk_count = count_unknowns(UNKNOWN_OUT)
    log_action(f"Unknowns after overrides: {unk_count}")

    # 4) Per-file summary
    rc3, out3, err3 = run_cmd(SUMMARY_CMD, 'tei_annotation_summary')

    elapsed = time.time() - start
    log_action(f"Pipeline completed in {elapsed:.2f}s")

    # Print the rolling action log
    print("\nLast 10 actions:")
    for line in ACTION_LOG:
        print(line)
    print()


class DebouncedRunner:
    def __init__(self, wait_seconds: float, fn):
        self.wait = wait_seconds
        self.fn = fn
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def trigger(self):
        with self._lock:
            if self._timer and self._timer.is_alive():
                self._timer.cancel()
            self._timer = threading.Timer(self.wait, self.fn)
            self._timer.daemon = True
            self._timer.start()


class CuratorFileHandler(FileSystemEventHandler):
    def __init__(self, watch_file: Path, debounced: DebouncedRunner):
        super().__init__()
        self.watch_file = str(watch_file)
        self.debounced = debounced

    def _is_target(self, path: str) -> bool:
        # Normalize both paths to absolute, case-sensitive
        try:
            return os.path.abspath(path) == self.watch_file
        except Exception:
            return False

    def on_modified(self, event):
        if not event.is_directory and self._is_target(event.src_path):
            log_action(f"Detected modification: {event.src_path}")
            self.debounced.trigger()

    def on_created(self, event):
        if not event.is_directory and self._is_target(event.src_path):
            log_action(f"Detected creation: {event.src_path}")
            self.debounced.trigger()

    def on_moved(self, event):
        # Some editors write to temp file then move
        dest = getattr(event, 'dest_path', '')
        if dest and self._is_target(dest):
            log_action(f"Detected move into place: {dest}")
            self.debounced.trigger()


def main():
    print(f"Watching: {WATCH_FILE}")
    print("Tip: Save the file to trigger overrides + re-annotation. Debounce: ~1s")

    debounced = DebouncedRunner(DEBOUNCE_SECONDS, pipeline_run)

    event_handler = CuratorFileHandler(WATCH_FILE, debounced)
    observer = Observer()
    observer.schedule(event_handler, str(WATCH_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopping watcher…")
        observer.stop()
    observer.join()


if __name__ == '__main__':
    main()
