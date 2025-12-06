#!/usr/bin/env python3
"""
시간대별 배출 로직 테스트 스크립트
"""

import sys
from datetime import datetime
from hwserial.serial_reader import get_current_time_slot, filter_phases_by_time

def test_time_slot():
    """현재 시간대 확인"""
    print("=" * 60)
    print("🕐 현재 시간대 테스트")
    print("=" * 60)

    current_time = datetime.now()
    slot, message = get_current_time_slot()

    print(f"현재 시각: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"현재 시간대: {slot}")
    print(f"안내 메시지: {message}")
    print()

    return slot

def test_filtering(current_slot):
    """필터링 로직 테스트"""
    print("=" * 60)
    print("🔍 필터링 로직 테스트")
    print("=" * 60)

    # 테스트용 전체 스케줄 (서버에서 받은 것으로 가정)
    full_schedule = [
        {
            "time": "morning",
            "items": [
                {"slot": 1, "medi_id": "M001", "count": 2}
            ]
        },
        {
            "time": "afternoon",
            "items": [
                {"slot": 2, "medi_id": "M002", "count": 1}
            ]
        },
        {
            "time": "evening",
            "items": [
                {"slot": 3, "medi_id": "M003", "count": 1}
            ]
        }
    ]

    print(f"📋 전체 스케줄: {len(full_schedule)}개 시간대")
    for phase in full_schedule:
        print(f"  - {phase['time']}: {len(phase['items'])}개 약품")
    print()

    if current_slot is None:
        print("⛔ 배출 불가 시간대 (00:00~06:00)")
        print("   → 필터링 결과: 빈 배열")
        filtered = []
    else:
        filtered = filter_phases_by_time(full_schedule, current_slot)
        print(f"✅ 필터링 결과 (시간대: {current_slot}): {len(filtered)}개")
        for phase in filtered:
            print(f"  - {phase['time']}: {len(phase['items'])}개 약품")
    print()

    return filtered

def test_scenarios():
    """시나리오별 테스트"""
    print("=" * 60)
    print("📖 시나리오 테스트")
    print("=" * 60)

    current_slot, _ = get_current_time_slot()
    h = datetime.now().hour

    scenarios = {
        "아침 시간대 (06-12)": {
            "applies": 6 <= h < 12,
            "expected": ["morning", "afternoon", "evening"]
        },
        "점심 시간대 (12-18)": {
            "applies": 12 <= h < 18,
            "expected": ["afternoon", "evening"]
        },
        "저녁 시간대 (18-24)": {
            "applies": 18 <= h < 24,
            "expected": ["evening"]
        },
        "배출 불가 (00-06)": {
            "applies": 0 <= h < 6,
            "expected": []
        }
    }

    for scenario_name, scenario_data in scenarios.items():
        if scenario_data["applies"]:
            print(f"✅ 현재 시나리오: {scenario_name}")
            print(f"   예상 배출 시간대: {scenario_data['expected']}")
            print()
            break

def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "시간대별 배출 로직 테스트" + " " * 22 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    # 1. 현재 시간대 확인
    current_slot = test_time_slot()

    # 2. 필터링 로직 테스트
    filtered = test_filtering(current_slot)

    # 3. 시나리오 테스트
    test_scenarios()

    print("=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)
    print()

    # 결과 요약
    if current_slot is None:
        print("⚠️  현재는 배출 불가 시간대입니다 (00:00~06:00)")
        print("   → RFID 스캔 시 '약물 복용 시간대가 아닙니다' 메시지 표시")
    else:
        print(f"ℹ️  현재 시간대: {current_slot}")
        print(f"   → RFID 스캔 시 {len(filtered)}개 시간대 배출 진행")
        if filtered:
            times = [f['time'] for f in filtered]
            print(f"   → 배출 순서: {' → '.join(times)}")
    print()

if __name__ == "__main__":
    main()
