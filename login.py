"""
카카오 로그인 & 세션 쿠키 저장 스크립트

사용법:
    python3 login.py

실행하면 브라우저 창이 열립니다.
카카오 로그인을 직접 완료하면 쿠키가 cookies.json에 자동 저장됩니다.
"""

import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

KAKAO_LOGIN_URL = "https://accounts.kakao.com/login?continue=https://calendar.kakao.com/"
CALENDAR_URL = "https://calendar.kakao.com"
COOKIES_PATH = Path(__file__).parent / "cookies.json"


def main():
    print("=" * 55)
    print("  카카오 로그인 & 쿠키 저장")
    print("=" * 55)
    print()
    print("  브라우저가 열리면 카카오 계정으로 로그인해 주세요.")
    print("  로그인 완료 후 캘린더 화면이 뜨면 자동으로 쿠키가 저장됩니다.")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        print("  [1/3] 카카오 로그인 페이지 접속 중...")
        page.goto(KAKAO_LOGIN_URL, wait_until="domcontentloaded")

        print("  [2/3] 로그인 완료를 기다리는 중... (최대 3분)")
        print("        브라우저에서 로그인해 주세요.")

        # 캘린더 페이지에서 실제 콘텐츠(캘린더 그리드)가 나타날 때까지 대기
        # 로그인 완료 → 캘린더로 리다이렉트 → SPA 렌더링 완료 순서
        try:
            page.wait_for_url(
                lambda url: "calendar.kakao.com" in url and "login" not in url,
                timeout=180_000,
            )
        except Exception:
            if "calendar.kakao.com" not in page.url:
                print("  [오류] 3분 안에 로그인되지 않았습니다. 다시 실행해 주세요.")
                browser.close()
                sys.exit(1)

        print("  캘린더 페이지 감지 — 렌더링 완료 대기 중...")

        # SPA라 networkidle 불가 → 5초 대기로 인증 쿠키 세팅 완료 보장
        page.wait_for_timeout(5_000)

        # 쿠키 저장 (all domains)
        print("  [3/3] 쿠키 저장 중...")
        cookies = context.cookies()

        # 인증 여부 검증: .kakao.com 도메인 쿠키 존재 확인
        kakao_cookies = [c for c in cookies if "kakao.com" in c.get("domain", "")]
        if not kakao_cookies:
            print("  [오류] 인증 쿠키를 가져오지 못했습니다. 로그인을 다시 시도해 주세요.")
            browser.close()
            sys.exit(1)

        with open(COOKIES_PATH, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        browser.close()

    print()
    print(f"  쿠키 저장 완료: {COOKIES_PATH}")
    print(f"  저장된 쿠키 수: {len(cookies)}개  (kakao.com 도메인: {len(kakao_cookies)}개)")
    print()
    print("  이제 check_auth.py를 실행해 접속 확인을 해주세요.")
    print("    python3 check_auth.py")


if __name__ == "__main__":
    main()
