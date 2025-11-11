#include <Arduino.h>
#include "globals.hpp"
#include "pins.hpp"


void testRFID() {
  Serial.println();
  Serial.println(F("--- RFID Test ---"));
  mfrc522.PCD_Init();
  mfrc522.PCD_AntennaOn();

  Serial.println(F("Place a tag near the reader for 5 seconds..."));
  const unsigned long start = millis();
  while (millis() - start < 5000UL) {
    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
      Serial.print(F("Tag UID: "));
      for (byte i = 0; i < mfrc522.uid.size; i++) {
        Serial.print(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " ");
        Serial.print(mfrc522.uid.uidByte[i], HEX);
      }
      Serial.println();
      mfrc522.PICC_HaltA();
      return;
    }
  }
  Serial.println(F("No tag detected."));
}

void diagnoseRFID() {
  Serial.println();
  Serial.println(F("--- RFID Detailed Diagnosis ---"));

  // 강한 재초기화
  mfrc522.PCD_Init(); delay(50);

  Serial.println(F("2. Verifying Pin Connections (Arduino Mega):"));
  Serial.print(F("  - RST Pin: ")); Serial.println((int)RFID_RST_PIN);
  Serial.print(F("  - SS/SDA Pin: ")); Serial.println((int)RFID_SS_PIN);
  Serial.println(F("  - MOSI Pin: 51"));
  Serial.println(F("  - MISO Pin: 50"));
  Serial.println(F("  - SCK Pin: 52"));

  Serial.println();
  Serial.println(F("3. Checking MFRC522 Firmware Version..."));
  byte version = mfrc522.PCD_ReadRegister(mfrc522.VersionReg);
  if (version == 0x00 || version == 0xFF) {
    Serial.println(F("  [ERROR] Communication FAILED!"));
    return;
  }
  Serial.print(F("  [OK] Firmware: 0x")); Serial.println(version, HEX);

  Serial.println();
  Serial.println(F("4. Performing PCD Self-Test..."));
  bool ok = mfrc522.PCD_PerformSelfTest();
  Serial.println(ok ? F("  [OK] Self-test passed.") : F("  [WARN] Self-test failed."));
  mfrc522.PCD_Init();

  Serial.println();
  Serial.println(F("5. Checking Antenna..."));
  mfrc522.PCD_AntennaOn();
  byte agc = mfrc522.PCD_GetAntennaGain();
  Serial.print(F("  - Antenna Gain: "));
  if (agc == 0) Serial.println(F("0 (Error or Off)"));
  else { Serial.print(F("0x")); Serial.println(agc, HEX); }
}
