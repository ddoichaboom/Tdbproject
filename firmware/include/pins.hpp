#pragma once
#include <Arduino.h>

// 핀/상수: 선언만 (정의는 pins.cpp)
extern const uint8_t SERVO1_PIN;
extern const uint8_t SERVO2_PIN;
extern const uint8_t RFID_RST_PIN;
extern const uint8_t RFID_SS_PIN;

// 솔레노이드 핀 배열
extern const uint8_t LOADING_SOLENOID_PINS[3];
extern const uint8_t DISPENSING_SOLENOID_PINS[3];

// 기타 공용 상수
extern const unsigned long RFID_RST_PULSE_MS;   // 50ms
extern const int SERVO_NEUTRAL;                 // 90
