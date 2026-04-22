"""
저장된 쿠키로 calendar.kakao.com 접속 확인 스크립트

사용법:
    python3 check_auth.py

cookies.json이 유효하면 캘린더 화면 스크린샷을 저장합니다.
만료된 경우 login.py를 다시 실행하라는 안내가 출력됩니다.
"""

import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CALENDAR_URL = "https://calendar.kakao.com"
COOKIES_PATH = Path(__file__).parent / "cookies.json"
SCREENSHOT_PATH = Path(__file__).parent / "auth_check.png"


def load_cookies() -> list:
    if not COOKIES_PATH.exists():
        print("[오류] cookies.json 파일이 없습니다.")
        print("  먼저 login.py를 실행해 주세요: python3 login.py")
        sys.exit(1)

    with open(COOKIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    print("=" * 55)
    print("  카카오 캘린더 접속 확인")
    print("=" * 55)
    print()

    cookies = load_cookies()
    print(f"  쿠키 로드: {len(cookies)}개")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
        )
        context.add_cookies(cookies)
        page = context.new_page()

        print("  캘린더 페이지 접속 중...")
        page.goto(CALENDAR_URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(5_000)  # SPA 렌더링 대기

        current_url = page.url
        print(f"  현재 URL: {current_url}")

        # 로그인 페이지로 리다이렉트됐는지 확인
        if "accounts.kakao.com" in current_url or "login" in current_url:
            print()
            print("  [실패] 쿠키가 만료됐습니다.")
            print("  login.py를 다시 실행해 주세요: python3 login.py")
            browser.close()
            sys.exit(1)

        # 로그인 버튼이 화면에 있으면 인증 실패
        login_btn = page.query_selector("a:has-text('로그인'), button:has-text('로그인')")
        if login_btn and login_btn.is_visible():
            print()
            print("  [실패] 캘린더 페이지에 '로그인' 버튼이 표시됩니다.")
            print("  쿠키가 올바르지 않습니다. login.py를 다시 실행해 주세요.")
            page.screenshot(path=str(SCREENSHOT_PATH))
            browser.close()
            sys.exit(1)

        # 스크린샷 저장
        page.screenshot(path=str(SCREENSHOT_PATH), full_page=False)
        browser.close()

    print()
    print("  [성공] 캘린더 접속 확인 완료!")
    print(f"  스크린샷 저장: {SCREENSHOT_PATH}")
    print()
    print("  auth_check.png 파일을 열어 캘린더 화면이 보이는지 확인해 주세요.")


if __name__ == "__main__":
    main()
