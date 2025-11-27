#include <Arduino.h>
#include <SPI.h>
#include "pins.hpp"
#include "globals.hpp"
#include "hardware.hpp"

void hardwareSetup() {
  Serial.begin(9600);
  while (!Serial) { /* wait */ }

  // 내장 LED를 출력으로 설정 (오류 표시용)
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW); // LED 끔

  // 솔레노이드 안전 초기화 (Active-Low: HIGH=OFF, LOW=ON)
  for (int i = 0; i < 3; i++) {
    pinMode(LOADING_SOLENOID_PINS[i], OUTPUT);
    digitalWrite(LOADING_SOLENOID_PINS[i], HIGH);  // OFF 상태
    pinMode(DISPENSING_SOLENOID_PINS[i], OUTPUT);
    digitalWrite(DISPENSING_SOLENOID_PINS[i], HIGH); // OFF 상태
  }

  // SPI/RC522 초기화
  SPI.begin();
  mfrc522.PCD_Init(RFID_SS_PIN, RFID_RST_PIN); // ★★★ SS, RST 핀 명시적 전달
  delay(50);

  // ★★★ RFID 리더기 초기화 성공 여부 검증 ★★★
  Serial.println(F("RFID Reader Self-Test..."));
  mfrc522.PCD_DumpVersionToSerial(); // 펌웨어 버전 출력
  bool init_ok = mfrc522.PCD_PerformSelfTest();

  if (!init_ok) {
    Serial.println(F("FATAL: RFID Reader initialization failed!"));
    Serial.println(F("Check wiring or reset the device."));
    // 초기화 실패 시 무한 루프에 진입하고 LED를 깜빡여 오류 알림
    while (true) {
      digitalWrite(LED_BUILTIN, HIGH);
      delay(100);
      digitalWrite(LED_BUILTIN, LOW);
      delay(100);
    }
  }
  Serial.println(F("RFID Reader OK."));
  mfrc522.PCD_AntennaOn();

  // 서보 초기화 (중립 위치 후 전력 절약)
  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);
  servo1.write(SERVO_NEUTRAL);
  servo2.write(SERVO_NEUTRAL);
  delay(300);
  servo1.detach();
  servo2.detach();
}

void printMenu() {
  Serial.println();
  Serial.println(F("--- Hardware Test Menu ---"));
  Serial.println(F("1. Test RFID Reader (Simple)"));
  Serial.println(F("2. Test Solenoid Actuators (Interactive)"));
  Serial.println(F("3. Test Servo Motors (Time-based)"));
  Serial.println(F("4. Diagnose RFID Reader (Detailed)"));
  Serial.print(F("Enter your choice: "));
}


