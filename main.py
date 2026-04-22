"""
풋살 강습 알림 메인 파이프라인

매주 월요일 08:30 자동 실행 (launchd)
또는 수동 실행: python3 main.py

흐름:
  1. 카카오 캘린더 크롤링 → 다음 화요일 '풋살' 일정 + 참석자 추출
  2. 메시지 생성
  3. 카카오 나에게 보내기
"""

import sys
from datetime import datetime
from pathlib import Path

from message import build_message
from kakao_sender import send_to_me
from scraper import scrape, CookieExpiredError


def main():
    print("=" * 55)
    print(f"  풋살 알림봇 실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # 1. 캘린더 크롤링
    print("\n[1/3] 카카오 캘린더 크롤링...")
    try:
        event = scrape(headless=True)
    except CookieExpiredError as e:
        alert = f"[풋살 알림봇] 카카오 캘린더 쿠키가 만료됐습니다.\n~/futsal_notifier 에서 login.py를 실행해 재로그인해 주세요."
        print(alert)
        send_to_me(alert)
        sys.exit(1)

    if event is None:
        print("화요일 풋살 일정 없음 → 발송 생략")
        sys.exit(0)

    if not event.get("attendees"):
        print("참석자 0명 → 발송 생략")
        sys.exit(0)

    # 2. 메시지 생성
    print("\n[2/3] 메시지 생성...")
    message = build_message(event)
    print("-" * 40)
    print(message)
    print("-" * 40)

    # 3. 발송
    print("\n[3/3] 카카오 나에게 보내기...")
    ok = send_to_me(message)

    if ok:
        print(f"\n완료! 참석자 {len(event['attendees'])}명 메시지 발송 성공")
    else:
        print("\n발송 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
