#!/usr/bin/env python3
"""
엣지 케이스 테스트
"""

from hwserial.serial_reader import filter_phases_by_time

def test_edge_case_1():
    """엣지 케이스 1: 빈 phases 배열"""
    print("=" * 60)
    print("Test 1: 빈 phases 배열")
    print("=" * 60)

    phases = []
    current_slot = "evening"

    result = filter_phases_by_time(phases, current_slot)

    print(f"입력: phases={phases}, current_slot={current_slot}")
    print(f"결과: {result}")
    print(f"✅ 통과: 빈 배열 반환" if result == [] else "❌ 실패")
    print()
    return result == []

def test_edge_case_2():
    """엣지 케이스 2: items가 빈 배열인 phase"""
    print("=" * 60)
    print("Test 2: items가 빈 배열")
    print("=" * 60)

    phases = [
        {"time": "morning", "items": []},
        {"time": "afternoon", "items": []},
        {"time": "evening", "items": []}
    ]
    current_slot = "evening"

    result = filter_phases_by_time(phases, current_slot)

    print(f"입력: 모든 items가 빈 배열")
    print(f"결과: {len(result)}개 phase")
    print(f"✅ 통과: evening phase 포함됨" if len(result) == 1 and result[0]["time"] == "evening" else "❌ 실패")
    print("주의: main()에서 'all(not p.get('items'))' 체크로 걸러짐")
    print()
    return len(result) == 1

def test_edge_case_3():
    """엣지 케이스 3: time 키가 없는 phase"""
    print("=" * 60)
    print("Test 3: time 키가 없는 phase")
    print("=" * 60)

    phases = [
        {"items": [{"slot": 1, "count": 1}]},  # time 키 없음
        {"time": "evening", "items": [{"slot": 2, "count": 1}]}
    ]
    current_slot = "evening"

    result = filter_phases_by_time(phases, current_slot)

    print(f"입력: time 키가 없는 phase 포함")
    print(f"결과: {len(result)}개 phase")
    print(f"✅ 통과: time 키 없는 건 제외됨" if len(result) == 1 else "❌ 실패")
    print()
    return len(result) == 1

def test_edge_case_4():
    """엣지 케이스 4: 알 수 없는 time 값"""
    print("=" * 60)
    print("Test 4: 알 수 없는 time 값")
    print("=" * 60)

    phases = [
        {"time": "unknown", "items": [{"slot": 1, "count": 1}]},
        {"time": "evening", "items": [{"slot": 2, "count": 1}]}
    ]
    current_slot = "evening"

    result = filter_phases_by_time(phases, current_slot)

    print(f"입력: time='unknown' phase 포함")
    print(f"결과: {len(result)}개 phase")
    print(f"✅ 통과: unknown은 제외됨" if len(result) == 1 else "❌ 실패")
    print()
    return len(result) == 1

def test_edge_case_5():
    """엣지 케이스 5: current_slot이 None"""
    print("=" * 60)
    print("Test 5: current_slot=None (배출 불가 시간대)")
    print("=" * 60)

    phases = [
        {"time": "morning", "items": [{"slot": 1, "count": 1}]},
        {"time": "afternoon", "items": [{"slot": 2, "count": 1}]},
        {"time": "evening", "items": [{"slot": 3, "count": 1}]}
    ]
    current_slot = None

    result = filter_phases_by_time(phases, current_slot)

    print(f"입력: current_slot=None (00:00~06:00)")
    print(f"결과: {result}")
    print(f"✅ 통과: 빈 배열 반환" if result == [] else "❌ 실패")
    print()
    return result == []

def test_edge_case_6():
    """엣지 케이스 6: 중복된 time 값"""
    print("=" * 60)
    print("Test 6: 중복된 time 값")
    print("=" * 60)

    phases = [
        {"time": "evening", "items": [{"slot": 1, "count": 1}]},
        {"time": "evening", "items": [{"slot": 2, "count": 1}]},
        {"time": "morning", "items": [{"slot": 3, "count": 1}]}
    ]
    current_slot = "evening"

    result = filter_phases_by_time(phases, current_slot)

    print(f"입력: evening이 2개")
    print(f"결과: {len(result)}개 phase")
    print(f"✅ 통과: 2개 모두 포함됨" if len(result) == 2 else "❌ 실패")
    print("주의: process_queue()가 순서대로 처리함")
    print()
    return len(result) == 2

def test_edge_case_7():
    """엣지 케이스 7: 점심 시간대에 아침약만 있는 경우"""
    print("=" * 60)
    print("Test 7: 점심 시간대에 아침약만 있는 경우")
    print("=" * 60)

    phases = [
        {"time": "morning", "items": [{"slot": 1, "count": 1}]}
    ]
    current_slot = "afternoon"

    result = filter_phases_by_time(phases, current_slot)

    print(f"입력: morning만 있음, current_slot=afternoon")
    print(f"결과: {result}")
    print(f"✅ 통과: 빈 배열 (아침약은 제외)" if result == [] else "❌ 실패")
    print("주의: main()에서 '배출할 약이 없습니다' 메시지 표시")
    print()
    return result == []

def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "엣지 케이스 테스트" + " " * 22 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    results = []

    results.append(("빈 배열", test_edge_case_1()))
    results.append(("items 빈 배열", test_edge_case_2()))
    results.append(("time 키 없음", test_edge_case_3()))
    results.append(("알 수 없는 time", test_edge_case_4()))
    results.append(("current_slot=None", test_edge_case_5()))
    results.append(("중복 time", test_edge_case_6()))
    results.append(("시간 지난 약", test_edge_case_7()))

    print("=" * 60)
    print("결과 요약")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print()
    print(f"총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 모든 엣지 케이스 통과!")
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패")

    print()

if __name__ == "__main__":
    main()
