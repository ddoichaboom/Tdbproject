// #include <SPI.h>
// #include <MFRC522.h>

// #include <Servo.h>

// // Pin definitions from Read.cpp
// #define SERVO1_PIN 30
// #define SERVO2_PIN 31
// #define RFID_RST_PIN 49
// #define RFID_SS_PIN 53

// MFRC522 mfrc522(RFID_SS_PIN, RFID_RST_PIN);
// Servo servo1;
// Servo servo2;

// // Solenoid Actuator (Relay) Pins
// const int loadingSolenoidPins[] = {22, 24, 26};
// const int dispensingSolenoidPins[] = {23, 25, 27};

// void setup() {
//   Serial.begin(9600);
//   while (!Serial) { ; }

//   // Safer Solenoid Initialization
//   for (int i = 0; i < 3; i++) {
//     digitalWrite(loadingSolenoidPins[i], HIGH);
//     pinMode(loadingSolenoidPins[i], OUTPUT);
//     digitalWrite(dispensingSolenoidPins[i], HIGH);
//     pinMode(dispensingSolenoidPins[i], OUTPUT);
//   }

//   pinMode(RFID_SS_PIN, OUTPUT);
//   digitalWrite(RFID_SS_PIN, HIGH); // 장치 비선택 상태로 시작

//   // Robust RFID Initialization
//   SPI.begin();
//   pinMode(RFID_RST_PIN, OUTPUT);
//   digitalWrite(RFID_RST_PIN, LOW);
//   delay(50);
//   digitalWrite(RFID_RST_PIN, HIGH);
//   delay(50);
//   mfrc522.PCD_Init();
//   delay(50);

//   servo1.attach(SERVO1_PIN);
//   servo2.attach(SERVO2_PIN);
//   servo1.write(90);
//   servo2.write(90);

//   printMenu();
// }

// void loop() {
//   if (Serial.available() > 0) {
//     char choice = Serial.read();
//     while(Serial.available() > 0) { Serial.read(); }

//     switch (choice) {
//       case '1': testRFID(); break;
//       case '2': testSolenoids(); break;
//       case '3': testServos(); break;
//       case '4': diagnoseRFID(); break;
//       default: Serial.println(F("Invalid choice. Please try again.")); break;
//     }
//     printMenu();
//   }
// }

// void printMenu() {
//   Serial.println();
//   Serial.println(F("--- Hardware Test Menu ---"));
//   Serial.println(F("1. Test RFID Reader (Simple)"));
//   Serial.println(F("2. Test Solenoid Actuators (Interactive)"));
//   Serial.println(F("3. Test Servo Motors (Time-based)"));
//   Serial.println(F("4. Diagnose RFID Reader (Detailed)"));
//   Serial.print(F("Enter your choice: "));
// }

// void testRFID() {
//   Serial.println();
//   Serial.println(F("--- RFID Test ---"));
  
//   // Perform a quick re-initialization for reliability
//   mfrc522.PCD_Init();
//   mfrc522.PCD_AntennaOn();

//   Serial.println(F("Place a tag near the reader for 5 seconds..."));
//   unsigned long startTime = millis();
//   while(millis() - startTime < 5000) {
//     if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
//       Serial.print(F("Tag UID: "));
//       for (byte i = 0; i < mfrc522.uid.size; i++) {
//         Serial.print(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " ");
//         Serial.print(mfrc522.uid.uidByte[i], HEX);
//       }
//       Serial.println();
//       mfrc522.PICC_HaltA();
//       return;
//     }
//   }
//   Serial.println(F("No tag detected."));
// }

// void diagnoseRFID() {
//     Serial.println();
//     Serial.println(F("--- RFID Detailed Diagnosis ---"));

//     // Force hard reset and re-initialize
//     Serial.println(F("1. Performing robust re-initialization..."));
//     pinMode(RFID_RST_PIN, OUTPUT);
//     digitalWrite(RFID_RST_PIN, LOW);
//     delay(50);
//     digitalWrite(RFID_RST_PIN, HIGH);
//     delay(50);
//     mfrc522.PCD_Init();
//     delay(50);

//     Serial.println();
//     Serial.println(F("2. Verifying Pin Connections (Arduino Mega):"));
//     Serial.print(F("  - RST Pin: ")); Serial.println(RFID_RST_PIN);
//     Serial.print(F("  - SS/SDA Pin: ")); Serial.println(RFID_SS_PIN);
//     Serial.println(F("  - MOSI Pin: 51"));
//     Serial.println(F("  - MISO Pin: 50"));
//     Serial.println(F("  - SCK Pin: 52"));

//     Serial.println();
//     Serial.println(F("3. Checking MFRC522 Firmware Version..."));
//     byte version = mfrc522.PCD_ReadRegister(mfrc522.VersionReg);
//     if (version == 0x00 || version == 0xFF) {
//         Serial.println(F("  [ERROR] Communication FAILED!"));
//         Serial.println(F("  - No MFRC522 board detected."));
//         Serial.println(F("  - This strongly suggests a hardware issue."));
//         Serial.println(F("  - Please re-check wiring and power supply."));
//         return;
//     }
//     Serial.print(F("  [OK] Communication successful. Firmware version: 0x"));
//     Serial.print(version, HEX);
//     if (version == 0x91) Serial.print(F(" (v1.0)"));
//     if (version == 0x92) Serial.print(F(" (v2.0)"));
//     Serial.println();

//     Serial.println();
//     Serial.println(F("4. Performing PCD (Proximity Coupling Device) Self-Test..."));
//     bool selfTestResult = mfrc522.PCD_PerformSelfTest();
//     if (selfTestResult) {
//         Serial.println(F("  [OK] Self-test passed. The board is likely healthy."));
//     } else {
//         Serial.println(F("  [WARNING] Self-test failed. The board might be faulty."));
//     }
//     mfrc522.PCD_Init();

//     Serial.println();
//     Serial.println(F("5. Checking Antenna..."));
//     mfrc522.PCD_AntennaOn();
//     byte antennaGain = mfrc522.PCD_GetAntennaGain();
//     Serial.print(F("  - Antenna Gain: "));
//     if (antennaGain == 0) {
//         Serial.println(F("0 (Error or Off)"));
//     } else {
//         Serial.print(F("0x"));
//         Serial.println(antennaGain, HEX);
//     }

//     Serial.println();
//     Serial.println(F("6. Ready for Card Detection (10 seconds)"));
//     Serial.println(F("  -> Please place a card or tag on the reader..."));
//     bool cardFound = false;
//     unsigned long startTime = millis();
//     while(millis() - startTime < 10000) {
//         if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
//             Serial.println(F("  [SUCCESS] Card Detected!"));
//             Serial.print(F("    - UID: "));
//             for (byte i = 0; i < mfrc522.uid.size; i++) {
//                 Serial.print(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " ");
//                 Serial.print(mfrc522.uid.uidByte[i], HEX);
//             }
//             Serial.println();
//             MFRC522::PICC_Type piccType = mfrc522.PICC_GetType(mfrc522.uid.sak);
//             Serial.print(F("    - Card Type: "));
//             Serial.println(mfrc522.PICC_GetTypeName(piccType));
//             mfrc522.PICC_HaltA();
//             cardFound = true;
//             break; 
//         }
//     }

//     if (!cardFound) {
//         Serial.println(F("  [FAILED] No card detected in 10 seconds."));
//         Serial.println(F("  - Try a different card or check antenna connection."));
//     }
//     Serial.println();
//     Serial.println(F("--- Diagnosis Complete ---"));
// }

// void testSolenoids() {
//     Serial.println();
//     Serial.println(F("--- Solenoid Test (Interactive) ---"));
//     while (true) {
//         Serial.println();
//         Serial.println(F("Select a slot to test:"));
//         Serial.println(F("  1. Slot 1 (Loading & Dispensing)"));
//         Serial.println(F("  2. Slot 2 (Loading & Dispensing)"));
//         Serial.println(F("  3. Slot 3 (Loading & Dispensing)"));
//         Serial.println(F("  Q. Quit to main menu"));
//         Serial.print(F("Enter choice: "));
//         String input = readSerialInput();
//         char choice = input.charAt(0);
//         if (input.equalsIgnoreCase("Q")) { break; }
//         int slotIndex = -1;
//         if (choice == '1') { slotIndex = 0; }
//         else if (choice == '2') { slotIndex = 1; }
//         else if (choice == '3') { slotIndex = 2; }
//         if (slotIndex != -1) {
//             Serial.println();
//             Serial.print(F("Testing Slot ")); Serial.println(slotIndex + 1);
//             Serial.println(F("  -> Loading..."));
//             digitalWrite(loadingSolenoidPins[slotIndex], LOW);
//             delay(1000);
//             digitalWrite(loadingSolenoidPins[slotIndex], HIGH);
//             delay(500);
//             Serial.println(F("  -> Dispensing..."));
//             digitalWrite(dispensingSolenoidPins[slotIndex], LOW);
//             delay(1000);
//             digitalWrite(dispensingSolenoidPins[slotIndex], HIGH);
//             delay(500);
//             Serial.println(F("Slot test complete."));
//         } else {
//             Serial.println(F("Invalid choice. Please enter 1, 2, 3, or Q."));
//         }
//     }
// }

// void testServos() {
//     Serial.println();
//     Serial.println(F("--- 360 Servo Test (Time-based) ---"));
//     while (true) {
//         Serial.println();
//         Serial.println(F("Select Direction:"));
//         Serial.println(F("  1. Forward"));
//         Serial.println(F("  2. Backward"));
//         Serial.println(F("  Q. Quit to main menu"));
//         Serial.print(F("Enter choice: "));
//         String dirInput = readSerialInput();
//         if (dirInput.equalsIgnoreCase("Q")) { break; }
//         char dirChoice = dirInput.charAt(0);
//         if (dirChoice != '1' && dirChoice != '2') {
//             Serial.println(F("Invalid direction. Please enter 1 or 2."));
//             continue;
//         }
//         Serial.print(F("Enter Speed (0-100): "));
//         String speedInput = readSerialInput();
//         int speed = speedInput.toInt();
//         if (speed < 0 || speed > 100) {
//             Serial.println(F("Invalid speed. Please enter a number between 0 and 100."));
//             continue;
//         }
//         Serial.print(F("Enter Duration in milliseconds (e.g., 2000 for 2s): "));
//         String durationInput = readSerialInput();
//         long duration = durationInput.toInt();
//         if (duration <= 0) {
//             Serial.println(F("Invalid duration. Please enter a positive number."));
//             continue;
//         }
//         int servoSpeed = map(speed, 0, 100, 0, 90);
//         int servo1Value, servo2Value;
//         if (dirChoice == '1') {
//             Serial.println(F("-> Moving Forward"));
//             servo1Value = 90 - servoSpeed;
//             servo2Value = 90 + servoSpeed;
//         } else {
//             Serial.println(F("-> Moving Backward"));
//             servo1Value = 90 + servoSpeed;
//             servo2Value = 90 - servoSpeed;
//         }
//         Serial.print(F("Running for ")); Serial.print(duration); Serial.println(F("ms..."));
//         servo1.write(servo1Value);
//         servo2.write(servo2Value);
//         delay(duration);
//         servo1.write(90);
//         servo2.write(90);
//         Serial.println(F("Movement complete. Motors stopped."));
//     }
// }

// String readSerialInput() {
//     String input = "";
//     while (true) {
//         if (Serial.available() > 0) {
//             char c = Serial.read();
//             if (c == '\n' || c == '\r') {
//                 if (input.length() > 0) { break; }
//             } else {
//                 input += c;
//             }
//         }
//     }
//     return input;
// }
