"""
메시지 생성 모듈

scraper.py의 결과를 받아 카카오톡 발송용 메시지 문자열을 생성합니다.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")


def build_message(event: dict) -> str:
    """
    event 예시:
    {
        "date_str": "4/28(화)",
        "location": "용산 실내구장",
        "start_time": "20",
        "end_time": "22",
        "attendees": ["권영은", "김푸름", "문소연"],
    }
    """
    date_str   = event["date_str"]
    location   = event["location"]
    start_time = event["start_time"]
    end_time   = event["end_time"]
    attendees  = event["attendees"]
    count      = len(attendees)

    # 코칭비: 10명 이상 12,500원 / 미만 15,000원
    fee = "12,500원" if count >= 10 else "15,000원"

    account_number = os.getenv("ACCOUNT_NUMBER", "")
    account_bank   = os.getenv("ACCOUNT_BANK", "")
    account_holder = os.getenv("ACCOUNT_HOLDER", "")

    names = "\n".join(attendees)

    message = f"""{date_str} 강습 명단 및 코칭비 입금 안내입니다
- 일시 : {date_str} {location} ({start_time}-{end_time})

- 참석명단 ({count}명)
{names}

- 코칭비 입금 안내
계좌 : {account_number} {account_bank} {account_holder}
금액 : {fee}"""

    return message


if __name__ == "__main__":
    # 테스트
    test_event = {
        "date_str": "4/28(화)",
        "location": "용산 실내구장",
        "start_time": "20",
        "end_time": "22",
        "attendees": ["권영은", "김여옥", "김유민", "김푸름", "문소연",
                      "박예은", "박지숙", "배선유", "이승혜", "이연주",
                      "이하경", "차민지"],
    }
    print(build_message(test_event))
