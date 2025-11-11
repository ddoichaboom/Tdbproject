#include "pins.hpp"

// === 실제 값 정의 ===
const uint8_t SERVO1_PIN = 30;
const uint8_t SERVO2_PIN = 31;
const uint8_t RFID_RST_PIN = 49;
const uint8_t RFID_SS_PIN  = 53;

const uint8_t LOADING_SOLENOID_PINS[3]   = {22, 24, 26};
const uint8_t DISPENSING_SOLENOID_PINS[3]= {23, 25, 27};

const unsigned long RFID_RST_PULSE_MS = 50;
const int SERVO_NEUTRAL = 90;
