#!/usr/bin/env python3
"""
솔레노이드 테스트 스크립트

Usage:
    python scripts/test_solenoid.py --slot 1 --type L    # 슬롯1 로딩만
    python scripts/test_solenoid.py --slot 2 --type D    # 슬롯2 배출만
    python scripts/test_solenoid.py --slot 3 --type B    # 슬롯3 로딩+배출
    python scripts/test_solenoid.py --all                # 전체 슬롯 테스트
"""

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from hwserial.arduino_link import open_serial, send_raw


def test_solenoid(ser, slot: int, test_type: str):
    """
    솔레노이드 테스트 실행

    Args:
        ser: 시리얼 포트 객체
        slot: 슬롯 번호 (1, 2, 3)
        test_type: 테스트 타입
            'L' - Loading만 테스트
            'D' - Dispensing만 테스트
            'B' - Both (로딩+배출) 테스트
    """
    type_map = {
        'L': 'Loading',
        'D': 'Dispensing',
        'B': 'Loading + Dispensing'
    }

    print(f"\n{'='*50}")
    print(f"슬롯 {slot} 테스트: {type_map.get(test_type, test_type)}")
    print(f"{'='*50}")

    cmd = f"TEST_SOLENOID,{slot},{test_type}"
    timeout = 5.0 if test_type in ['L', 'D'] else 8.0  # Both는 더 긴 시간 필요

    ok, response = send_raw(ser, cmd, timeout=timeout)

    if ok:
        print(f"✓ 성공: {response}")
        return True
    else:
        print(f"✗ 실패: {response}")
        return False


def test_all_slots(ser):
    """전체 슬롯 순차 테스트 (로딩+배출)"""
    print("\n" + "="*50)
    print("전체 슬롯 테스트 시작")
    print("="*50)

    results = []
    for slot in [1, 2, 3]:
        print(f"\n>>> 슬롯 {slot} 테스트 중...")
        success = test_solenoid(ser, slot, 'B')
        results.append((slot, success))

        if slot < 3:  # 마지막 슬롯이 아니면 대기
            print("\n다음 슬롯까지 2초 대기...")
            import time
            time.sleep(2)

    # 결과 요약
    print("\n" + "="*50)
    print("테스트 결과 요약")
    print("="*50)
    for slot, success in results:
        status = "✓ 성공" if success else "✗ 실패"
        print(f"슬롯 {slot}: {status}")

    all_success = all(success for _, success in results)
    print("\n전체 결과:", "✓ 모두 성공" if all_success else "✗ 일부 실패")
    return all_success


def main():
    parser = argparse.ArgumentParser(
        description="솔레노이드 테스트 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  슬롯 1 로딩 테스트:
    python scripts/test_solenoid.py --slot 1 --type L

  슬롯 2 배출 테스트:
    python scripts/test_solenoid.py --slot 2 --type D

  슬롯 3 로딩+배출 테스트:
    python scripts/test_solenoid.py --slot 3 --type B

  전체 슬롯 테스트:
    python scripts/test_solenoid.py --all
        """
    )

    parser.add_argument("--slot", type=int, choices=[1, 2, 3],
                        help="테스트할 슬롯 번호 (1, 2, 3)")
    parser.add_argument("--type", choices=['L', 'D', 'B'],
                        help="테스트 타입: L(Loading), D(Dispensing), B(Both)")
    parser.add_argument("--all", action="store_true",
                        help="전체 슬롯 테스트 (로딩+배출)")

    args = parser.parse_args()

    # 인자 검증
    if not args.all and (args.slot is None or args.type is None):
        parser.error("--slot과 --type을 함께 지정하거나, --all을 사용하세요")

    if args.all and (args.slot is not None or args.type is not None):
        parser.error("--all은 --slot, --type과 함께 사용할 수 없습니다")

    # 시리얼 포트 열기
    print("Arduino 연결 중...")
    try:
        ser = open_serial()
    except Exception as e:
        print(f"❌ 시리얼 포트 열기 실패: {e}")
        print("\n해결 방법:")
        print("1. Arduino가 연결되어 있는지 확인")
        print("2. config/.env에서 TDB_SERIAL_PORT 확인")
        print("3. 다른 프로그램에서 포트를 사용 중인지 확인")
        sys.exit(1)

    print(f"✓ Arduino 연결 성공: {ser.port}")

    # 테스트 실행
    try:
        if args.all:
            success = test_all_slots(ser)
        else:
            success = test_solenoid(ser, args.slot, args.type)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n테스트 중단됨 (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        sys.exit(1)
    finally:
        ser.close()
        print("\n시리얼 포트 닫음")


if __name__ == "__main__":
    main()
