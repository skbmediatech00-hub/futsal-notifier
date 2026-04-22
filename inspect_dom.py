"""
카카오 캘린더 DOM 구조 인스펙터

풋살 일정 더블클릭 후 우측 참석자 패널의 HTML 구조를 출력합니다.
scraper.py 작성 전 DOM 파악용 1회성 스크립트입니다.
"""

import json
from pathlib import Path
from datetime import date, timedelta
from playwright.sync_api import sync_playwright

CALENDAR_URL = "https://calendar.kakao.com"
COOKIES_PATH = Path(__file__).parent / "cookies.json"


def next_tuesday() -> date:
    today = date.today()
    days_until_tuesday = (1 - today.weekday()) % 7  # 화요일 = weekday 1
    if days_until_tuesday == 0:
        days_until_tuesday = 7
    return today + timedelta(days=days_until_tuesday)


def main():
    with open(COOKIES_PATH) as f:
        cookies = json.load(f)

    target = next_tuesday()
    print(f"대상 날짜: {target.month}월 {target.day}일 (화요일)")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        context.add_cookies(cookies)
        page = context.new_page()

        print("캘린더 접속 중...")
        page.goto(CALENDAR_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5_000)

        # 알림 권한 팝업 닫기
        try:
            close_btn = page.locator("button:has-text('닫기')").first
            if close_btn.is_visible(timeout=3_000):
                close_btn.click()
                print("알림 팝업 닫음")
                page.wait_for_timeout(1_000)
        except Exception:
            pass

        # 화면에 보이는 일정 중 '풋살' 포함된 것 찾기
        print("풋살 일정 탐색 중...")
        page.wait_for_timeout(2_000)

        # 현재 화면에 보이는 이벤트 텍스트 전체 출력 (디버깅용)
        all_events = page.locator("[class*='event'], [class*='schedule'], [class*='item']")
        print(f"감지된 요소 수: {all_events.count()}")

        # 풋살 텍스트 포함 요소 찾기
        futsal_els = page.locator("text=풋살")
        count = futsal_els.count()
        print(f"'풋살' 텍스트 요소 수: {count}")

        for i in range(min(count, 5)):
            el = futsal_els.nth(i)
            try:
                tag = el.evaluate("e => e.tagName")
                cls = el.evaluate("e => e.className")
                txt = el.inner_text()
                print(f"  [{i}] <{tag}> class={cls!r} text={txt!r}")
            except Exception as e:
                print(f"  [{i}] 오류: {e}")

        if count == 0:
            print("현재 화면에 풋살 일정이 없습니다. 다음 주 화요일로 이동이 필요할 수 있어요.")
            # 페이지 전체 텍스트에서 풋살 확인
            body_text = page.inner_text("body")
            if "풋살" in body_text:
                print("→ body에는 '풋살' 텍스트 존재 (hidden 요소일 가능성)")
            page.screenshot(path="inspect_calendar.png")
            print("스크린샷 저장: inspect_calendar.png")
            browser.close()
            return

        # 첫 번째 풋살 일정 더블클릭
        first_futsal = futsal_els.first
        print("\n풋살 일정 더블클릭...")
        first_futsal.dblclick()
        page.wait_for_timeout(4_000)

        page.screenshot(path="inspect_after_dblclick.png")
        print("더블클릭 후 스크린샷: inspect_after_dblclick.png")

        # 현재 URL 확인 (상세 페이지로 이동했는지)
        print(f"현재 URL: {page.url}")

        # 참석자 패널 HTML 추출
        # 우측 패널 후보 셀렉터들 시도
        selectors = [
            "[class*='attendee']",
            "[class*='participant']",
            "[class*='member']",
            "[class*='invite']",
            "text=참가",
            "text=불참",
            "text=초대",
        ]

        print("\n--- 참석자 관련 DOM 탐색 ---")
        for sel in selectors:
            try:
                els = page.locator(sel)
                c = els.count()
                if c > 0:
                    print(f"\n셀렉터 {sel!r}: {c}개 발견")
                    for i in range(min(c, 3)):
                        el = els.nth(i)
                        try:
                            html = el.evaluate("e => e.outerHTML")
                            print(f"  [{i}] {html[:300]}")
                        except Exception:
                            pass
            except Exception as e:
                print(f"셀렉터 {sel!r} 오류: {e}")

        # 우측 패널 전체 HTML 저장
        try:
            # 페이지 우측 영역 (상세 페이지에서 참석자 패널)
            right_panel = page.locator("body").evaluate("""() => {
                // 참가, 불참, 초대 텍스트 포함 요소의 부모를 찾음
                const els = document.querySelectorAll('*');
                for (const el of els) {
                    if (el.children.length > 3 && el.innerText &&
                        (el.innerText.includes('참가') || el.innerText.includes('불참')) &&
                        el.innerText.includes('명')) {
                        return el.outerHTML.substring(0, 3000);
                    }
                }
                return '참석자 패널을 찾지 못했습니다';
            }""")
            print("\n--- 참석자 패널 HTML (최대 3000자) ---")
            print(right_panel)
        except Exception as e:
            print(f"패널 추출 오류: {e}")

        browser.close()
        print("\n완료. 스크린샷과 위 출력을 확인해주세요.")


if __name__ == "__main__":
    main()
