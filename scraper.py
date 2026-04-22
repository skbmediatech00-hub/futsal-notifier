"""
카카오 캘린더 스크래퍼

다음 화요일의 '풋살' 일정에서 참석 확정자 목록과 일정 정보를 추출합니다.

반환값 예시:
{
    "date_str": "4/28(화)",
    "location": "용산 실내구장",
    "start_time": "20",
    "end_time": "22",
    "attendees": ["권영은", "김푸름", "문소연"],
}
"""

import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from typing import Optional
from playwright.sync_api import sync_playwright

# GitHub Actions 등 CI 환경 감지
IS_CI = os.getenv("CI", "false").lower() == "true"


class CookieExpiredError(Exception):
    pass

CALENDAR_URL = "https://calendar.kakao.com"
COOKIES_PATH = Path(__file__).parent / "cookies.json"
KEYWORD = "풋살"


def next_tuesday() -> date:
    today = date.today()
    days = (1 - today.weekday()) % 7  # 화요일 = weekday 1
    if days == 0:
        days = 7
    return today + timedelta(days=days)


def extract_korean_name(text: str) -> Optional[str]:
    """
    'SKB 권영은M', '*문소연*', '박예은' 등에서 한글 이름(2~4글자) 추출.
    여러 한글 덩어리가 있으면 2글자 이상 중 가장 긴 것 선택.
    """
    matches = re.findall(r"[가-힣]{2,4}", text)
    if not matches:
        return None
    # 가장 긴 한글 덩어리 = 이름일 가능성 높음
    return max(matches, key=len)


def parse_time(time_str: str) -> str:
    """
    '오후 8:00' → '20', '오전 10:00' → '10'
    """
    m = re.search(r"(오전|오후)\s*(\d+):(\d+)", time_str)
    if not m:
        return time_str
    ampm, hour, minute = m.group(1), int(m.group(2)), int(m.group(3))
    if ampm == "오후" and hour != 12:
        hour += 12
    if ampm == "오전" and hour == 12:
        hour = 0
    return f"{hour:02d}" if minute == 0 else f"{hour:02d}:{minute:02d}"


def scrape(headless: bool = True) -> Optional[dict]:
    target = next_tuesday()
    target_label = f"{target.month}월 {target.day}일 화요일"
    print(f"대상: {target_label} / 키워드: '{KEYWORD}'")

    if not COOKIES_PATH.exists():
        print("[오류] cookies.json 없음. login.py를 먼저 실행하세요.")
        sys.exit(1)

    with open(COOKIES_PATH) as f:
        cookies = json.load(f)

    with sync_playwright() as p:
        # CI(GitHub Actions)에선 시스템 Chrome 없음 → Playwright 내장 Chromium 사용
        if IS_CI:
            browser = p.chromium.launch(headless=True)
        else:
            browser = p.chromium.launch(headless=headless, channel="chrome")
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        context.add_cookies(cookies)
        page = context.new_page()

        # 로그인 확인
        page.goto(CALENDAR_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5_000)

        if "accounts.kakao.com" in page.url or "login" in page.url:
            browser.close()
            raise CookieExpiredError("쿠키 만료. login.py를 다시 실행하세요.")

        # 알림 팝업 닫기
        try:
            btn = page.locator("button:has-text('닫기')").first
            if btn.is_visible(timeout=3_000):
                btn.click()
                page.wait_for_timeout(1_000)
        except Exception:
            pass

        # ── 대상 화요일의 풋살 일정 찾기 ──────────────────────────────
        # screen_out 요소: "오후 8:00, 참석, 풋살(용산 실내) - 코칭, ..., 4월 28일 화요일 ..."
        print(f"'{target_label}' 풋살 일정 탐색 중...")

        event_el = None
        saved_screen_out_text = ""  # 더블클릭 전에 저장
        screen_outs = page.locator(".screen_out").all()
        for el in screen_outs:
            try:
                txt = el.inner_text()
                if KEYWORD in txt and target_label in txt:
                    saved_screen_out_text = txt  # 시간 파싱용으로 저장
                    # 실제 클릭 가능한 이벤트 조상 요소 (a 또는 button)
                    ancestor = el.locator("xpath=ancestor::a[1] | ancestor::button[1]").first
                    if ancestor.count() == 0:
                        ancestor = el.locator("xpath=ancestor::div[@role='button'][1]").first
                    event_el = ancestor if ancestor.count() > 0 else el
                    print(f"  일정 발견: {txt[:80]}")
                    break
            except Exception:
                continue

        if event_el is None:
            print(f"[안내] {target_label}에 '{KEYWORD}' 일정이 없습니다. 발송 생략.")
            browser.close()
            return None

        # ── 일정 더블클릭 → 상세 페이지 이동 ─────────────────────────
        event_el.dblclick()
        page.wait_for_timeout(4_000)
        print(f"  상세 페이지 URL: {page.url}")

        # ── 일정 기본 정보 추출 ────────────────────────────────────────
        # 제목
        title = ""
        try:
            title = page.locator(".tf_title, input[id='newTitle']").first.input_value()
        except Exception:
            pass

        # 날짜/시간 (input value)
        start_time_raw = ""
        end_time_raw = ""
        try:
            time_inputs = page.locator("input.tf_comm.tf_date").all()
            # 시작 오전/오후 선택 값
            time_selects = page.locator(".opt_select .link_selected span:not(.screen_out), .opt_select .link_selected span:not(.ico_calendar)").all()
            time_texts = [el.inner_text().strip() for el in time_selects if el.inner_text().strip()]
            # '오전'/'오후' + 시 + 분 순서로 4개씩 (시작, 종료)
            # 실제 표시 텍스트로 조합
        except Exception:
            pass

        # 장소
        location = ""
        try:
            loc_input = page.locator("input[placeholder='장소 입력'], .tf_place").first
            if loc_input.count() > 0:
                location = loc_input.input_value().strip()
        except Exception:
            pass

        # screen_out 에서 시간 파싱 (더 안정적)
        event_time_info = {"date": target_label, "start": "", "end": "", "location": location}
        # 더블클릭 전에 저장한 screen_out 텍스트로 시간 파싱
        # 예: "오후 8:00, 참석, 풋살(용산 실내) - 코칭, ..., 4월 28일 화요일 오후 8:00 ~ 오후 10:00"
        if saved_screen_out_text:
            times = re.findall(r"(?:오전|오후)\s*\d+:\d+", saved_screen_out_text)
            if len(times) >= 2:
                # screen_out 형식: "오후 7:00, 참석, ..., 오후 7:00 ~ 오후 9:00"
                # 마지막 두 개가 실제 시작/종료 시간
                event_time_info["start"] = parse_time(times[-2])
                event_time_info["end"] = parse_time(times[-1])

        # 장소: 제목에서 괄호 안 추출 시도 (예: '풋살(용산 실내) - 코칭' → '용산 실내')
        if not location:
            m = re.search(r"풋살\(([^)]+)\)", title)
            if m:
                location = m.group(1)

        # ── 참석자 목록 추출 ───────────────────────────────────────────
        print("  참석자 목록 추출 중...")

        # 참석자 요약 텍스트 확인
        summary = ""
        try:
            summary = page.locator(".txt_inviteon").first.inner_text()
            print(f"  참석 현황: {summary}")
        except Exception:
            pass

        # unit_invite 항목 순회
        attendees = []
        items = page.locator("li:has(.unit_invite)").all()
        print(f"  전체 초대 항목 수: {len(items)}")

        for item in items:
            try:
                # 참석 여부 판단
                has_ok = item.locator(".ico_ok").count() > 0
                has_no = item.locator(".ico_no").count() > 0

                if not has_ok or has_no:
                    continue  # 불참 또는 미정 제외

                # 이름 추출: unit_invite 내 텍스트에서 한글 이름 파싱
                name_text = item.inner_text().strip()
                name = extract_korean_name(name_text)
                if name:
                    attendees.append(name)
                    print(f"    ✓ 참석: {name_text!r} → {name}")
            except Exception as e:
                print(f"    항목 처리 오류: {e}")
                continue

        browser.close()

    # 날짜 포맷: "4/28(화)"
    date_str = f"{target.month}/{target.day}(화)"

    result = {
        "date_str": date_str,
        "location": location,
        "start_time": event_time_info["start"],
        "end_time": event_time_info["end"],
        "attendees": sorted(attendees),  # 가나다 순
    }

    print(f"\n  최종 결과: {result}")
    return result


if __name__ == "__main__":
    # 테스트 실행 시 headless=False로 화면 확인 가능
    result = scrape(headless=False)
    if result:
        print("\n=== 스크래핑 완료 ===")
        print(f"일정: {result['date_str']} {result['location']} ({result['start_time']}-{result['end_time']})")
        print(f"참석자 ({len(result['attendees'])}명): {', '.join(result['attendees'])}")
    else:
        print("해당 주 화요일 풋살 일정 없음.")
