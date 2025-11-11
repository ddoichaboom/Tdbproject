#pragma once

// 공용 초기화/메뉴
void hardwareSetup();     // setup()에서 호출
void printMenu();         // 메뉴 출력

// 기존 테스트 함수들을 옮길 계획이라면 우선 선언만
void testRFID();
void diagnoseRFID();
void testSolenoids();
void testServos();
