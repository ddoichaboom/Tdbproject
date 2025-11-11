#include <Arduino.h>
#include "hardware.hpp"
#include "globals.hpp"  // mfrc522
#include "pins.hpp"
#include "servos.hpp"



// 점심후 -> HOME 은 2000+2500=4500ms

static void handleSerialCommand();
static bool dispenseSlot(int slot, int count); // TODO: 실제 동작은 내 로직으로



// UID를 대문자 16진수로(공백 없이) 변환
static String uidToHexString() {
  String s;
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) s += "0";
    s += String(mfrc522.uid.uidByte[i], HEX);
  }
  s.toUpperCase();
  return s;
}

void setup() {
  hardwareSetup();            // SPI/RC522/서보/릴레이 초기화 (네가 만든 함수)
  Serial.println(F("READY")); // 선택: 파이 쪽 초기 연결 확인용
}

void loop() {
    // 1) RFID 감지 → UID 한 줄 출력 (기존)
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String uid = uidToHexString();
    Serial.println(uid);
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    delay(500);
  }

  handleSerialCommand();
}


// 그대로 교체해서 사용
static void handleSerialCommand() {
  static String buf;

  while (Serial.available() > 0) {
    char c = Serial.read();

    // 줄바꿈으로 한 명령 종료
    if (c == '\n' || c == '\r') {
      buf.trim();
      if (buf.length() == 0) {
        // 빈 줄이면 무시
        continue;
      }

      // -----------------------------
      // 1) DISPENSE,<slot>,<count>
      // -----------------------------
      if (buf.startsWith("DISPENSE")) {
        int first  = buf.indexOf(',');
        int second = buf.indexOf(',', first + 1);
        if (first < 0 || second < 0) {
          Serial.println("ERR,BAD_ARGS,DISPENSE");
          buf = "";
          continue;
        }
        int slot  = buf.substring(first + 1, second).toInt();
        int count = buf.substring(second + 1).toInt();

        // 유효성 (필요시 범위 조정)
        if (slot < 1 || slot > 3 || count <= 0) {
          Serial.print("ERR,OUT_OF_RANGE,"); Serial.print(slot);
          Serial.print(","); Serial.println(count);
          buf = "";
          continue;
        }

        bool ok = dispenseSlot(slot, count);
        if (ok) {
          Serial.print("OK,"); Serial.print(slot); Serial.print(","); Serial.println(count);
        } else {
          Serial.print("ERR,DISPENSE,"); Serial.print(slot); Serial.print(","); Serial.println(count);
        }
      }
      // -----------------------------
      // 2) HOME
      // -----------------------------
      else if (buf.equals("HOME") || buf.equals("STEP,HOME")) {
        servoReturnHome();
        Serial.println("OK,HOME");
      }
      // 3) STEP,NEXT : 한 칸 전진
      else if (buf.equals("STEP,NEXT")) {
        servoStepNext();
        Serial.println("OK,STEP,NEXT");
      }
      // -----------------------------
      // 4) TEST_SOLENOID,<slot>,<type>
      //    slot: 1,2,3  type: L(loading), D(dispensing), B(both)
      // -----------------------------
      else if (buf.startsWith("TEST_SOLENOID")) {
        int c1 = buf.indexOf(',');
        int c2 = buf.indexOf(',', c1 + 1);
        if (c1 < 0 || c2 < 0) {
          Serial.println("ERR,BAD_ARGS,TEST_SOLENOID");
          buf = "";
          continue;
        }
        int slot = buf.substring(c1 + 1, c2).toInt();
        char type = toupper(buf.substring(c2 + 1).charAt(0));

        // 유효성 검증
        if (slot < 1 || slot > 3) {
          Serial.print("ERR,INVALID_SLOT,"); Serial.println(slot);
          buf = "";
          continue;
        }
        if (type != 'L' && type != 'D' && type != 'B') {
          Serial.print("ERR,INVALID_TYPE,"); Serial.println(type);
          buf = "";
          continue;
        }

        int idx = slot - 1;

        // 테스트 실행
        if (type == 'L' || type == 'B') {
          Serial.print("TESTING_LOADING,"); Serial.println(slot);
          digitalWrite(LOADING_SOLENOID_PINS[idx], LOW);
          delay(1000);
          digitalWrite(LOADING_SOLENOID_PINS[idx], HIGH);
          delay(500);
        }

        if (type == 'D' || type == 'B') {
          Serial.print("TESTING_DISPENSING,"); Serial.println(slot);
          digitalWrite(DISPENSING_SOLENOID_PINS[idx], LOW);
          delay(1000);
          digitalWrite(DISPENSING_SOLENOID_PINS[idx], HIGH);
          delay(500);
        }

        Serial.print("OK,TEST_SOLENOID,"); Serial.print(slot);
        Serial.print(","); Serial.println(type);
      }
            // ...기존 else if들 위/아래 아무데나...
      else if (buf.startsWith("JOG")) {
        int c1 = buf.indexOf(',');
        if (c1 < 0) { Serial.println("ERR,BAD_ARGS,JOG"); buf = ""; return; }
        int c2 = buf.indexOf(',', c1 + 1);
        int c3 = (c2 >= 0) ? buf.indexOf(',', c2 + 1) : -1;
      
        char dir = toupper(buf.substring(c1 + 1, (c2 < 0 ? buf.length() : c2)).charAt(0));
        if (dir != 'F' && dir != 'B') { Serial.println("ERR,BAD_DIR"); buf = ""; return; }
      
        unsigned long ms = 0;
        if (c2 < 0) { Serial.println("ERR,BAD_ARGS,JOG"); buf = ""; return; }
      
        if (c3 < 0) {
          // JOG,DIR,MS  -> 기본 속도(50%) 사용
          ms = buf.substring(c2 + 1).toInt();
          if (ms <= 0) { Serial.println("ERR,BAD_MS"); buf = ""; return; }
          servoJog(dir, ms, 50);  
          Serial.print("OK,JOG,"); Serial.print(dir); Serial.print(",50,"); Serial.println(ms);
        } else {
          // JOG,DIR,SPD,MS
          int speed = buf.substring(c2 + 1, c3).toInt();
          ms = buf.substring(c3 + 1).toInt();
          if (ms <= 0) { Serial.println("ERR,BAD_MS"); buf = ""; return; }
          servoJog(dir, ms, speed);
          Serial.print("OK,JOG,"); Serial.print(dir); Serial.print(","); Serial.print(speed);
          Serial.print(","); Serial.println(ms);
        }
      }

      // -----------------------------
      // 5) 알 수 없는 명령
      // -----------------------------
      else {
        Serial.print("ERR,UNKNOWN,"); Serial.println(buf);
      }

      // 다음 명령 대비
      buf = "";
    }
    else {
      // 버퍼 축적 (너무 길어지면 안전하게 리셋)
      buf += c;
      if (buf.length() > 80) {  // 길이 제한은 취향껏
        buf = "";
        Serial.println("ERR,BUF_OVERFLOW");
      }
    }
  }
}


static bool dispenseSlot(int slot, int count) {
  // TODO: 네 실제 로직으로 교체 (아래는 예시: 솔레노이드만 1초씩)
  int idx = slot - 1;
  if (idx < 0 || idx >= 3) return false;
  for (int i=0; i<count; i++) {
        digitalWrite(LOADING_SOLENOID_PINS[idx], LOW);
        delay(1000);
        digitalWrite(LOADING_SOLENOID_PINS[idx], HIGH);
        delay(300);
        digitalWrite(DISPENSING_SOLENOID_PINS[idx], LOW);
        delay(1000);
        digitalWrite(DISPENSING_SOLENOID_PINS[idx], HIGH);
        delay(300);
  }
  return true;
}



