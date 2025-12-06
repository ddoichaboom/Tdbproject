#include <Arduino.h>
#include "globals.hpp"   // extern Servo servo1, servo2
#include "pins.hpp"      // SERVO_NEUTRAL
#include "servos.hpp"

// ===== 내부 상태/상수: 여기서만 정의 =====
static uint8_t g_servoStage = 0;                 // 0=HOME, 1=아침후, 2=점심후
static const int           kSERVO_STEP_SPEED = 50;   // %
static const unsigned long kSERVO_MS_STEP1   = 2000; // HOME->1
static const unsigned long kSERVO_MS_STEP2   = 2500; // 1->2
// 2->HOME = 4500 (= 2000+2500)
// ========================================

void servoNeutral() {
  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);

  servo1.write(SERVO_NEUTRAL);
  servo2.write(SERVO_NEUTRAL);
  delay(200);

  servo1.detach();
  servo2.detach();
}

void servoMoveFB(char dir, int speedPercent, unsigned long ms) {
  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);

  int s = constrain(speedPercent, 0, 100);
  int servoSpeed = map(s, 0, 100, 0, 90);
  int v1, v2;
  if (dir == 'F') { v1 = SERVO_NEUTRAL - servoSpeed; v2 = SERVO_NEUTRAL + servoSpeed; }
  else            { v1 = SERVO_NEUTRAL + servoSpeed; v2 = SERVO_NEUTRAL - servoSpeed; }

  servo1.write(v1);
  servo2.write(v2);
  delay(ms);

  servo1.detach();
  servo2.detach();
}

void servoStepNext() {
  if (g_servoStage == 0) {
    servoNeutral(); delay(100);
    servoMoveFB('F', kSERVO_STEP_SPEED, kSERVO_MS_STEP1);
    servoNeutral(); delay(100);
    g_servoStage = 1;
  } else if (g_servoStage == 1) {
    servoNeutral(); delay(100);
    servoMoveFB('F', kSERVO_STEP_SPEED, kSERVO_MS_STEP2);
    servoNeutral(); delay(100);
    g_servoStage = 2;
  }
  // g_servoStage==2면 더 전진 안 함
}

void servoReturnHome() {
  if (g_servoStage == 2) {
    servoNeutral(); delay(100);
    servoMoveFB('B', kSERVO_STEP_SPEED, kSERVO_MS_STEP2);
    servoNeutral(); delay(100);
    g_servoStage = 1;
  }
  if (g_servoStage == 1) {
    servoNeutral(); delay(100);
    servoMoveFB('B', kSERVO_STEP_SPEED, kSERVO_MS_STEP1);
    servoNeutral(); delay(100);
    g_servoStage = 0;
  }
}

void servoRunSequenceReturnToHome() {
  servoNeutral(); delay(100);
  servoMoveFB('F', 50, 2000);
  servoMoveFB('F', 50, 2500);
  servoNeutral(); delay(150);
  servoMoveFB('B', 50, 4500);
  servoNeutral(); delay(150);
  g_servoStage = 0;
}

uint8_t servoGetStage() {
  return g_servoStage;
}

// 응급 조작(JOG) — 헤더와 동일하게 'static' 빼고 구현
void    servoJog(char dir, unsigned long ms, int speedPercent=50) 
{
  int sp = constrain(speedPercent, 0, 100);
  ms = constrain(ms, 100UL, 15000UL);  // 안전상 한도(100~15000ms)
  servoNeutral(); delay(100);
  servoMoveFB(dir, sp, ms);
  servoNeutral(); delay(100);
}
