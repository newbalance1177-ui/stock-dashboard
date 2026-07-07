"""生成物(DB・ダッシュボード)を git commit & push する。"""
import subprocess
import sys
import time
from datetime import date

from config import BASE_DIR

MAX_PUSH_ATTEMPTS = 3


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, cwd=BASE_DIR, check=True, capture_output=True, text=True
    )


def has_changes() -> bool:
    result = run("git", "status", "--porcelain")
    return bool(result.stdout.strip())


def push_with_retry() -> None:
    # 同時実行等でリモートが進んでいた場合に備え、pull --rebase + push を数回リトライする
    for attempt in range(1, MAX_PUSH_ATTEMPTS + 1):
        try:
            run("git", "pull", "--rebase", "origin", "main")
            run("git", "push", "origin", "HEAD:main")
            return
        except subprocess.CalledProcessError as exc:
            if attempt == MAX_PUSH_ATTEMPTS:
                raise
            print(
                f"[deploy] push attempt {attempt} failed, retrying: {exc.stderr}",
                file=sys.stderr,
            )
            time.sleep(3)


def main() -> None:
    try:
        run("git", "add", "data", "docs")

        if not has_changes():
            print("[deploy] no changes to commit")
            return

        message = f"Automated update: {date.today().isoformat()}"
        run("git", "commit", "-m", message)
        push_with_retry()
        print(f"[deploy] pushed: {message}")
    except subprocess.CalledProcessError as exc:
        print(f"[deploy] git command failed: {exc.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
