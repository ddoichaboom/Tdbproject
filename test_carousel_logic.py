#!/usr/bin/env python3
"""
회전판 동작 안전성 테스트
"""

def _stage_for_time_key(time_key: str) -> int:
    """시간대 → 스테이지 매핑"""
    return {"morning": 0, "afternoon": 1, "evening": 2}.get(time_key, 0)

def simulate_carousel(filtered_phases):
    """
    회전판 동작 시뮬레이션

    Args:
        filtered_phases: 필터링된 시간대 목록

    Returns:
        (movements, final_stage, is_safe)
        - movements: 이동 내역
        - final_stage: 최종 위치
        - is_safe: 안전성 (역방향 이동 없음)
    """
    current_stage = 0  # HOME에서 시작
    movements = []
    is_safe = True

    # 필터링된 phases를 순서대로 정렬
    order = {"morning": 0, "afternoon": 1, "evening": 2}
    sorted_phases = sorted(filtered_phases, key=lambda p: order.get(p.get("time", ""), 99))

    for phase in sorted_phases:
        time_key = phase.get("time", "")
        target = _stage_for_time_key(time_key)

        # 이동 체크
        if target < current_stage:
            # 역방향 이동 감지 (HOME 복귀 필요)
            movements.append(f"⚠️  RESET: stage {current_stage} → HOME → {target} ({time_key})")
            is_safe = False  # HOME 복귀가 필요한 경우
            current_stage = 0  # HOME으로 리셋

        if target > current_stage:
            # 정방향 이동
            steps = target - current_stage
            movements.append(f"✅ MOVE: stage {current_stage} → {target} ({time_key}, {steps} step)")
            current_stage = target
        elif target == current_stage:
            # 제자리
            movements.append(f"🔵 STAY: stage {target} ({time_key})")

    # 최종 HOME 복귀
    if current_stage > 0:
        movements.append(f"🏠 RETURN: stage {current_stage} → HOME")

    return movements, current_stage, is_safe

def test_scenario_1():
    """시나리오 1: 아침 시간대 (모든 시간대 배출)"""
    print("=" * 60)
    print("시나리오 1: 아침 시간대 (06:00~12:00)")
    print("=" * 60)

    phases = [
        {"time": "morning", "items": [{"slot": 1}]},
        {"time": "afternoon", "items": [{"slot": 2}]},
        {"time": "evening", "items": [{"slot": 3}]}
    ]

    movements, final_stage, is_safe = simulate_carousel(phases)

    print("필터링된 시간대: morning, afternoon, evening")
    print("\n회전판 동작:")
    for m in movements:
        print(f"  {m}")

    print(f"\n최종 위치: stage {final_stage}")
    print(f"안전성: {'✅ 안전 (순방향만)' if is_safe else '⚠️  주의 (역방향 포함)'}")
    print()

    return is_safe

def test_scenario_2():
    """시나리오 2: 점심 시간대 (점심, 저녁 배출)"""
    print("=" * 60)
    print("시나리오 2: 점심 시간대 (12:00~18:00)")
    print("=" * 60)

    phases = [
        {"time": "afternoon", "items": [{"slot": 2}]},
        {"time": "evening", "items": [{"slot": 3}]}
    ]

    movements, final_stage, is_safe = simulate_carousel(phases)

    print("필터링된 시간대: afternoon, evening")
    print("\n회전판 동작:")
    for m in movements:
        print(f"  {m}")

    print(f"\n최종 위치: stage {final_stage}")
    print(f"안전성: {'✅ 안전 (순방향만)' if is_safe else '⚠️  주의 (역방향 포함)'}")
    print()

    return is_safe

def test_scenario_3():
    """시나리오 3: 저녁 시간대 (저녁만 배출)"""
    print("=" * 60)
    print("시나리오 3: 저녁 시간대 (18:00~24:00)")
    print("=" * 60)

    phases = [
        {"time": "evening", "items": [{"slot": 3}]}
    ]

    movements, final_stage, is_safe = simulate_carousel(phases)

    print("필터링된 시간대: evening")
    print("\n회전판 동작:")
    for m in movements:
        print(f"  {m}")

    print(f"\n최종 위치: stage {final_stage}")
    print(f"안전성: {'✅ 안전 (순방향만)' if is_safe else '⚠️  주의 (역방향 포함)'}")
    print()

    return is_safe

def test_scenario_4():
    """시나리오 4: 역순 phases (정렬 테스트)"""
    print("=" * 60)
    print("시나리오 4: 역순 phases (서버가 역순으로 보낸 경우)")
    print("=" * 60)

    phases = [
        {"time": "evening", "items": [{"slot": 3}]},
        {"time": "morning", "items": [{"slot": 1}]},
        {"time": "afternoon", "items": [{"slot": 2}]}
    ]

    movements, final_stage, is_safe = simulate_carousel(phases)

    print("입력 순서: evening, morning, afternoon")
    print("정렬 후 순서: morning, afternoon, evening")
    print("\n회전판 동작:")
    for m in movements:
        print(f"  {m}")

    print(f"\n최종 위치: stage {final_stage}")
    print(f"안전성: {'✅ 안전 (정렬됨)' if is_safe else '⚠️  주의'}")
    print()

    return is_safe

def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 13 + "회전판 동작 안전성 테스트" + " " * 17 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    results = []

    results.append(("아침 시간대", test_scenario_1()))
    results.append(("점심 시간대", test_scenario_2()))
    results.append(("저녁 시간대", test_scenario_3()))
    results.append(("역순 입력", test_scenario_4()))

    print("=" * 60)
    print("안전성 검증 결과")
    print("=" * 60)

    for name, is_safe in results:
        status = "✅ 안전" if is_safe else "⚠️  주의"
        print(f"{status} - {name}")

    total = len(results)
    safe_count = sum(1 for _, s in results if s)

    print()
    print(f"총 {total}개 시나리오 중 {safe_count}개 안전 ({safe_count/total*100:.0f}%)")

    if safe_count == total:
        print("\n🎉 모든 시나리오에서 안전하게 동작!")
        print("   → 순방향 이동만 발생 (역방향 없음)")
    else:
        print(f"\n⚠️  {total - safe_count}개 시나리오에서 역방향 이동 발생")
        print("   → process_queue()의 HOME 리셋 로직이 처리함")

    print()

if __name__ == "__main__":
    main()
