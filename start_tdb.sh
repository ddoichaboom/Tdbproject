#!/bin/bash
# TDB Dashboard auto-start script (stable version)

set -e

# 디스플레이 설정 (라즈베리파이 모니터)
export DISPLAY=:0
export XAUTHORITY=/home/tdb/.Xauthority

# 프로젝트 디렉터리 이동
cd /home/tdb/Tdbproject

# 가상환경 활성화
source .venv/bin/activate

# 애플리케이션 실행
exec /home/tdb/Tdbproject/.venv/bin/python /home/tdb/Tdbproject/main.py "$@"

