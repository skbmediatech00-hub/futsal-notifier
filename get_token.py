"""
카카오 Access Token / Refresh Token 발급 스크립트

사용법:
    python3 get_token.py

저장된 카카오 쿠키를 이용해 자동으로 인가 코드를 받아
.env에 토큰을 저장합니다.

사전 조건:
    - login.py로 cookies.json 저장 완료
    - 카카오 개발자 콘솔에서 Redirect URI로 https://localhost 등록 완료
    - 동의항목에서 '카카오톡 메시지 전송' 활성화 완료
"""

import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ENV_PATH = Path(__file__).parent / ".env"
COOKIES_PATH = Path(__file__).parent / "cookies.json"
load_dotenv(ENV_PATH)

REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "")
REDIRECT_URI = "https://localhost"
AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"


def update_env(key: str, value: str):
    content = ENV_PATH.read_text(encoding="utf-8")
    pattern = rf"^{key}=.*$"
    new_line = f"{key}={value}"
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content += f"\n{new_line}"
    ENV_PATH.write_text(content, encoding="utf-8")


def get_auth_code() -> str:
    """저장된 쿠키로 Playwright를 통해 인가 코드 자동 획득"""
    params = {
        "client_id": REST_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "talk_message",
    }
    auth_url = f"{AUTH_URL}?{urlencode(params)}"

    with open(COOKIES_PATH) as f:
        cookies = json.load(f)

    auth_code = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome")
        # ignore_https_errors: localhost 인증서 오류 무시
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
        )
        context.add_cookies(cookies)
        page = context.new_page()

        # 요청 가로채기: localhost로 가는 순간 URL에서 code 추출
        def on_request(request):
            nonlocal auth_code
            url = request.url
            if "localhost" in url and "code=" in url:
                m = re.search(r"[?&]code=([^&]+)", url)
                if m:
                    auth_code = m.group(1)

        page.on("request", on_request)

        print("  인가 페이지 접속 중...")
        try:
            page.goto(auth_url, wait_until="domcontentloaded", timeout=15_000)
            page.wait_for_timeout(2_000)
        except Exception:
            pass

        # 동의 버튼이 있으면 클릭
        try:
            agree_btn = page.locator("#acceptBtn, button:has-text('동의하고 계속하기'), button:has-text('허용')")
            if agree_btn.count() > 0 and agree_btn.first.is_visible(timeout=3_000):
                print("  동의 화면 감지 → 동의 클릭...")
                agree_btn.first.click()
                page.wait_for_timeout(3_000)
        except Exception:
            pass

        # request 이벤트로 못 잡은 경우 현재 URL 확인
        if not auth_code:
            current_url = page.url
            if "localhost" in current_url and "code=" in current_url:
                m = re.search(r"[?&]code=([^&]+)", current_url)
                if m:
                    auth_code = m.group(1)

        # 자동 캡처 실패 시 주소창 URL 수동 입력 fallback
        if not auth_code:
            print()
            print("  자동 캡처 실패 — 브라우저 주소창의 URL을 복사해서 붙여넣어 주세요.")
            print("  (https://localhost/?code=... 형태)")
            manual = input("  URL: ").strip()
            m = re.search(r"[?&]code=([^&]+)", manual)
            if m:
                auth_code = m.group(1)

        browser.close()

    return auth_code


def main():
    print("=" * 55)
    print("  카카오 토큰 발급")
    print("=" * 55)
    print()

    if not REST_API_KEY:
        print("[오류] .env에 KAKAO_REST_API_KEY가 없습니다.")
        return

    if not COOKIES_PATH.exists():
        print("[오류] cookies.json이 없습니다. login.py를 먼저 실행하세요.")
        return

    # 1. 인가 코드 자동 획득
    print("  [1/3] 인가 코드 획득 중 (Playwright 자동화)...")
    auth_code = get_auth_code()

    if not auth_code:
        print("[오류] 인가 코드를 획득하지 못했습니다.")
        print("  카카오 개발자 콘솔에서 아래를 확인해 주세요:")
        print("  1. Redirect URI에 https://localhost 등록됐는지")
        print("  2. 동의항목에서 '카카오톡 메시지 전송' 활성화됐는지")
        return

    print(f"  인가 코드 획득: {auth_code[:10]}...")

    # 2. Access Token / Refresh Token 발급
    print("  [2/3] 토큰 발급 중...")
    token_data = {
        "grant_type": "authorization_code",
        "client_id": REST_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": auth_code,
    }
    if CLIENT_SECRET:
        token_data["client_secret"] = CLIENT_SECRET

    resp = requests.post(TOKEN_URL, data=token_data)

    if resp.status_code != 200:
        print(f"[오류] 토큰 발급 실패: {resp.status_code}")
        print(resp.text)
        return

    data = resp.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if not access_token:
        print(f"[오류] 응답에 access_token 없음: {data}")
        return

    update_env("KAKAO_ACCESS_TOKEN", access_token)
    update_env("KAKAO_REFRESH_TOKEN", refresh_token)

    print(f"  Access Token  : {access_token[:15]}...")
    print(f"  Refresh Token : {refresh_token[:15]}...")

    # 3. 나에게 보내기 테스트
    print("  [3/3] 나에게 보내기 테스트...")
    test_resp = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {access_token}"},
        data={
            "template_object": '{"object_type":"text","text":"[풋살 알림봇] 토큰 발급 완료! 정상 동작합니다 ✓","link":{"web_url":"https://calendar.kakao.com"}}'
        },
    )

    print()
    if test_resp.status_code == 200:
        print("  [완료] 토큰 저장 및 테스트 메시지 발송 성공!")
        print("  카카오톡에서 테스트 메시지를 확인하세요.")
    else:
        print(f"  [경고] 테스트 발송 실패: {test_resp.status_code}")
        print(f"  {test_resp.text}")
        print("  동의항목에서 '카카오톡 메시지 전송'이 활성화됐는지 확인하세요.")


if __name__ == "__main__":
    main()
