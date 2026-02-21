#include "BluetoothSerial.h"
#include "ESP32Servo.h"

BluetoothSerial SerialBT;
Servo myServo;

const int ledPin = 2;
const int servoPin = 13; // You can use GPIO 13, 12, 14, etc.

void setup() {
  Serial.begin(115200);
  pinMode(ledPin, OUTPUT);

  // Setup Servo
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  myServo.setPeriodHertz(50);    // Standard 50hz servo
  myServo.attach(servoPin, 500, 2400); // Attach with min/max pulse widths

  SerialBT.begin("ESP32_Robot_Link"); 
  Serial.println("Waiting for Python command...");
}

void loop() {
  if (SerialBT.available()) {
    String incomingData = SerialBT.readStringUntil('\n');
    incomingData.trim(); 

    if (incomingData.length() > 0) {
      digitalWrite(ledPin, HIGH); // Flash LED when any data arrives
    }

    if (incomingData == "MOVE_Z_DOWN") {
      myServo.write(0);  // Move to 0 degrees
      SerialBT.println("ACK: Servo moved down");
    }
    else if (incomingData == "MOVE_Z_UP") {
      myServo.write(180); // Move to 180 degrees
      SerialBT.println("ACK: Servo moved up");
    }
    
    // Small delay to let the LED be visible before turning off
    delay(100);
    digitalWrite(ledPin, LOW);
  }
  delay(10); 
}