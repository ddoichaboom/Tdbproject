#pragma once
#include <Arduino.h>



void     servoNeutral();                               // 두 서보 중립(90)
void     servoMoveFB(char dir, int speedPercent, unsigned long ms); // 'F'/'B'
void     servoStepNext();                              // 한 칸 전진 (0→1, 1→2)
void     servoReturnHome();                            // 현재 단계→HOME(0)
void     servoRunSequenceReturnToHome();               // F50% 2s → F50% 2.5s → B50% 4.5s → HOME
uint8_t  servoGetStage();                              // 0/1/2
void    servoJog(char dir, unsigned long ms, int speedPercent=50);