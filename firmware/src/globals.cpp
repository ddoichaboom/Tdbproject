#include "globals.hpp"
#include "pins.hpp"

// 전역 객체 정의
MFRC522 mfrc522(RFID_SS_PIN, RFID_RST_PIN);
Servo servo1;
Servo servo2;
