"""
카카오 나에게 보내기 모듈

- Access Token으로 메시지 발송
- 토큰 만료 시 Refresh Token으로 자동 갱신 후 재발송
- 갱신된 토큰은 .env에 자동 저장
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

SEND_URL    = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
REFRESH_URL = "https://kauth.kakao.com/oauth/token"


def _update_env(key: str, value: str):
    content = ENV_PATH.read_text(encoding="utf-8")
    pattern = rf"^{key}=.*$"
    new_line = f"{key}={value}"
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content += f"\n{new_line}"
    ENV_PATH.write_text(content, encoding="utf-8")


def _refresh_access_token() -> str:
    """Refresh Token으로 새 Access Token 발급 후 .env 갱신"""
    refresh_token  = os.getenv("KAKAO_REFRESH_TOKEN")
    rest_api_key   = os.getenv("KAKAO_REST_API_KEY")
    client_secret  = os.getenv("KAKAO_CLIENT_SECRET", "")

    if not refresh_token:
        print("[오류] KAKAO_REFRESH_TOKEN이 없습니다. get_token.py를 다시 실행하세요.")
        sys.exit(1)

    data = {
        "grant_type":    "refresh_token",
        "client_id":     rest_api_key,
        "refresh_token": refresh_token,
    }
    if client_secret:
        data["client_secret"] = client_secret

    resp = requests.post(REFRESH_URL, data=data)
    if resp.status_code != 200:
        print(f"[오류] 토큰 갱신 실패: {resp.status_code} {resp.text}")
        sys.exit(1)

    result = resp.json()
    new_access_token = result["access_token"]
    _update_env("KAKAO_ACCESS_TOKEN", new_access_token)

    # Refresh Token도 새로 발급된 경우 갱신 (만료 임박 시 함께 발급됨)
    if "refresh_token" in result:
        _update_env("KAKAO_REFRESH_TOKEN", result["refresh_token"])
        print("  Refresh Token도 갱신됨")

    # 환경변수 메모리 갱신
    os.environ["KAKAO_ACCESS_TOKEN"] = new_access_token
    print(f"  Access Token 갱신 완료: {new_access_token[:15]}...")
    return new_access_token


def send_to_me(text: str) -> bool:
    """
    나에게 보내기 API 호출.
    토큰 만료(401) 시 자동 갱신 후 1회 재시도.
    성공 시 True, 실패 시 False 반환.
    """
    access_token = os.getenv("KAKAO_ACCESS_TOKEN")

    template = json.dumps({
        "object_type": "text",
        "text": text,
        "link": {"web_url": "https://calendar.kakao.com"},
    }, ensure_ascii=False)

    def _call(token: str) -> requests.Response:
        return requests.post(
            SEND_URL,
            headers={"Authorization": f"Bearer {token}"},
            data={"template_object": template},
        )

    resp = _call(access_token)

    # 토큰 만료 → 갱신 후 재시도
    if resp.status_code == 401:
        print("  Access Token 만료 → 자동 갱신 중...")
        access_token = _refresh_access_token()
        resp = _call(access_token)

    if resp.status_code == 200:
        return True
    else:
        print(f"[오류] 메시지 발송 실패: {resp.status_code} {resp.text}")
        return False


if __name__ == "__main__":
    # 테스트 발송
    test_msg = "[풋살 알림봇] 테스트 메시지입니다."
    ok = send_to_me(test_msg)
    print("발송 성공!" if ok else "발송 실패")
