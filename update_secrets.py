"""
GitHub Actions 실행 후 갱신된 Access/Refresh Token을 GitHub Secrets에 업데이트.
GH_TOKEN 환경변수(Personal Access Token)가 필요합니다.
"""

import os
import re
import subprocess
from pathlib import Path

ENV_PATH = Path(".env")


def read_env_value(key: str) -> str:
    if not ENV_PATH.exists():
        return ""
    content = ENV_PATH.read_text(encoding="utf-8")
    m = re.search(rf"^{key}=(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def set_secret(key: str, value: str):
    if not value:
        return
    result = subprocess.run(
        ["gh", "secret", "set", key, "--body", value],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  Secrets 업데이트: {key}")
    else:
        print(f"  Secrets 업데이트 실패 ({key}): {result.stderr.strip()}")


def main():
    if not os.getenv("GH_TOKEN"):
        print("GH_TOKEN 없음 → Secrets 업데이트 건너뜀")
        return

    print("갱신된 토큰 Secrets 업데이트 중...")
    for key in ("KAKAO_ACCESS_TOKEN", "KAKAO_REFRESH_TOKEN"):
        value = read_env_value(key)
        if value:
            set_secret(key, value)


if __name__ == "__main__":
    main()
