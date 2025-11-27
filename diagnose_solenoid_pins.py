#!/usr/bin/env python3
"""
솔레노이드 핀 출력 테스트 (핀 자체 점검)

각 핀의 HIGH/LOW 전환이 정상 작동하는지 시리얼 모니터로 확인
"""

import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from hwserial.arduino_link import open_serial, send_raw


def test_pin_output(ser, slot: int, pin_type: str):
    """
    특정 핀의 출력 상태를 수동으로 제어하여 테스트

    Args:
        slot: 1, 2, 3
        pin_type: 'L' (Loading) or 'D' (Dispensing)
    """
    pin_map = {
        (1, 'L'): 22, (1, 'D'): 23,
        (2, 'L'): 24, (2, 'D'): 25,
        (3, 'L'): 26, (3, 'D'): 27,
    }

    pin = pin_map.get((slot, pin_type))
    name = "Loading" if pin_type == 'L' else "Dispensing"

    print(f"\n{'='*60}")
    print(f"슬롯 {slot} {name} 핀 테스트 (핀 {pin})")
    print(f"{'='*60}")
    print("테스트 방법:")
    print("1. 릴레이 모듈의 해당 채널 LED를 주시하세요")
    print("2. 핀이 LOW(ON)일 때 LED가 켜져야 합니다")
    print("3. 핀이 HIGH(OFF)일 때 LED가 꺼져야 합니다")
    print(f"{'='*60}\n")

    # 5회 반복 테스트
    for i in range(5):
        print(f"[{i+1}/5] LOW (ON) - 릴레이 LED 켜짐 확인...")
        ok, resp = send_raw(ser, f"TEST_SOLENOID,{slot},{pin_type}", timeout=3.0)

        if not ok:
            print(f"  ✗ 실패: {resp}")
            return False

        print(f"  ✓ {resp}")
        time.sleep(2)

    print(f"\n슬롯 {slot} {name} 핀 테스트 완료")
    return True


def main():
    print("="*60)
    print("솔레노이드 핀 출력 테스트")
    print("="*60)
    print("\n이 테스트는 각 핀의 출력이 정상인지 확인합니다.")
    print("릴레이 모듈을 보면서 LED 점멸을 확인하세요.\n")

    # 시리얼 연결
    try:
        ser = open_serial(baud_rate=9600)
        print(f"✓ Arduino 연결: {ser.port}\n")
    except Exception as e:
        print(f"✗ Arduino 연결 실패: {e}")
        sys.exit(1)

    # 전체 슬롯 테스트
    slots_to_test = [
        (1, 'L'), (1, 'D'),
        (2, 'L'), (2, 'D'),
        (3, 'L'), (3, 'D'),
    ]

    results = []

    for slot, pin_type in slots_to_test:
        success = test_pin_output(ser, slot, pin_type)
        results.append((slot, pin_type, success))

        if slot < 3 or pin_type == 'L':
            print("\n다음 테스트까지 3초 대기...\n")
            time.sleep(3)

    # 결과 요약
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)

    for slot, pin_type, success in results:
        name = "Loading" if pin_type == 'L' else "Dispensing"
        status = "✓ 정상" if success else "✗ 비정상"
        print(f"슬롯 {slot} {name:11s} (핀 {22+slot*2-2 if pin_type=='L' else 23+slot*2-2}): {status}")

    failed = [r for r in results if not r[2]]
    if failed:
        print(f"\n⚠️  문제 발견: {len(failed)}개 핀에서 오류")
        print("\n원인 가능성:")
        print("1. Arduino 핀 불량")
        print("2. 릴레이 모듈 채널 불량")
        print("3. 배선 접촉 불량")
    else:
        print("\n✓ 모든 핀 정상 작동")
        print("\n→ 코드/핀 출력은 정상입니다.")
        print("→ 릴레이 접점 또는 솔레노이드 자체를 확인하세요.")

    ser.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n테스트 중단")
        sys.exit(130)
