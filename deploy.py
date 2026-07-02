"""生成物(DB・ダッシュボード)を git commit & push する。"""
import subprocess
import sys
from datetime import date

from config import BASE_DIR


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, cwd=BASE_DIR, check=True, capture_output=True, text=True
    )


def has_changes() -> bool:
    result = run("git", "status", "--porcelain")
    return bool(result.stdout.strip())


def main() -> None:
    try:
        run("git", "add", "data", "output")

        if not has_changes():
            print("[deploy] no changes to commit")
            return

        message = f"Automated update: {date.today().isoformat()}"
        run("git", "commit", "-m", message)
        # push前にリモートの最新変更を取り込む(同時実行等でリモートが進んでいた場合の保険)
        run("git", "pull", "--rebase", "origin", "main")
        run("git", "push")
        print(f"[deploy] pushed: {message}")
    except subprocess.CalledProcessError as exc:
        print(f"[deploy] git command failed: {exc.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
