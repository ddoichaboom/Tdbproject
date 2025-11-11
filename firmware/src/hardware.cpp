#include <Arduino.h>
#include <SPI.h>
#include "pins.hpp"
#include "globals.hpp"
#include "hardware.hpp"

void hardwareSetup() {
  Serial.begin(9600);
  while (!Serial) { /* wait */ }

  // 솔레노이드 안전 초기화
  for (int i = 0; i < 3; i++) {
    digitalWrite(LOADING_SOLENOID_PINS[i], HIGH);
    pinMode(LOADING_SOLENOID_PINS[i], OUTPUT);
    digitalWrite(DISPENSING_SOLENOID_PINS[i], HIGH);
    pinMode(DISPENSING_SOLENOID_PINS[i], OUTPUT);
  }

  // SPI/RC522
  pinMode(RFID_SS_PIN, OUTPUT);
  digitalWrite(RFID_SS_PIN, HIGH);   // 비선택
  pinMode(RFID_RST_PIN, OUTPUT);
  SPI.begin();
  digitalWrite(RFID_RST_PIN, LOW);   delay(RFID_RST_PULSE_MS);
  digitalWrite(RFID_RST_PIN, HIGH);  delay(RFID_RST_PULSE_MS);
  mfrc522.PCD_Init();                delay(50);
  mfrc522.PCD_AntennaOn();

  // 서보
  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);
  servo1.write(SERVO_NEUTRAL);
  servo2.write(SERVO_NEUTRAL);
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


