# scripts/recovery_jog.py
import argparse
from hwserial.arduino_link import open_serial, jog, step_next, step_home

def main():
    ap = argparse.ArgumentParser(description="Emergency JOG / STEP control")
    ap.add_argument("--dir", choices=["F","B"])
    ap.add_argument("--ms", type=int)
    ap.add_argument("--speed", type=int, default=None)
    ap.add_argument("--step", choices=["NEXT","HOME"])
    args = ap.parse_args()

    if not args.step and not args.dir:
        ap.error("하나 이상 선택 필요: --step 또는 --dir/--ms")

    with open_serial() as ser:
        if args.step:
            if args.step == "NEXT":
                ok, msg = step_next(ser)
            else:
                ok, msg = step_home(ser)
            print("STEP ->", msg)
            return

        ok, msg = jog(ser, args.dir, args.ms, args.speed)
        print("JOG ->", msg)

if __name__ == "__main__":
    main()
