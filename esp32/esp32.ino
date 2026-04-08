#include "max6675.h"
#include "BluetoothSerial.h"
#include "ESP32Servo.h"

// --- Configuration & Pins ---
const int PIN_THERMO_SO = 18;
const int PIN_THERMO_CS = 5;
const int PIN_THERMO_SCK = 19;
const int PIN_MOSFET = 23;
const int PIN_SERVO = 13;
const int PIN_LED = 2;

// --- Objects ---
BluetoothSerial SerialBT;
Servo zAxisServo;
MAX6675 thermocouple(PIN_THERMO_SCK, PIN_THERMO_CS, PIN_THERMO_SO);

// --- Global State ---
bool ironEnabled = false;
float setpoint = 300.0; 
float currentTemp = 0, pidOutput = 0;      
float lastError = 0, cumError = 0;

// --- PID Constants ---
const float Kp = 15.0; 
const float Ki = 0.01; 
const float Kd = 25.0;   
const float MAX_DUTY = 75.0;

// --- Timing ---
unsigned long lastPidTime = 0;
unsigned long windowStartTime;
unsigned long ledOffTime = 0;
const int SAMPLE_INTERVAL = 200; 
const int PWM_WINDOW_SIZE = 1500; 

void setup() {
  Serial.begin(115200);
  
  pinMode(PIN_MOSFET, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_MOSFET, LOW);
  
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  zAxisServo.setPeriodHertz(50); 
  zAxisServo.attach(PIN_SERVO, 500, 2400);

  SerialBT.begin("ESP32_Robot_Link"); 
  windowStartTime = millis();
}

void loop() {
  unsigned long now = millis();

  // Task 1: Handle LED logic
  updateStatusLED(now);

  // Task 2: Listen for Bluetooth commands
  handleBluetoothCommands(now);

  // Task 3: Run PID (Every 200ms)
  if (now - lastPidTime >= SAMPLE_INTERVAL) {
    runTemperatureControl(now);
    lastPidTime = now;
  }

  // Task 4: Execute PWM for the MOSFET
  executeHeaterPWM(now);
}

// --- Helper Functions ---

void handleBluetoothCommands(unsigned long now) {
  if (!SerialBT.available()) return;

  String cmd = SerialBT.readStringUntil('\n');
  cmd.trim(); 

  // Visual feedback for command received
  digitalWrite(PIN_LED, HIGH);
  ledOffTime = now + 100; 

  if (cmd == "MOVE_Z_DOWN") {
    zAxisServo.write(0);
    SerialBT.println("ACK: Z_DOWN");
  } 
  else if (cmd == "MOVE_Z_UP") {
    zAxisServo.write(160);
    SerialBT.println("ACK: Z_UP");
  } 
  else if (cmd == "IRON_ON") {
    ironEnabled = true;
    SerialBT.println("ACK: IRON_ON");
  } 
  else if (cmd == "IRON_OFF") {
    shutdownHeater();
    SerialBT.println("ACK: IRON_OFF");
  } 
  else if (cmd.startsWith("SET_TEMP_")) {
    setpoint = cmd.substring(9).toFloat();
    int setpointInt = (int)setpoint;
    SerialBT.print("ACK: SET_TEMP_"); SerialBT.println(setpointInt);
  }
}

void runTemperatureControl(unsigned long now) {
  currentTemp = thermocouple.readCelsius();
  // Stream data
  SerialBT.println(currentTemp);

  if (!ironEnabled || isnan(currentTemp) || currentTemp < 1.0) {
    pidOutput = 0;
    return;
  }

  float error = setpoint - currentTemp;
  
  // Anti-Windup Logic: Only integrate if near setpoint and not saturated
  bool saturated = (pidOutput >= MAX_DUTY && error > 0) || (pidOutput <= 0 && error < 0);
  if (abs(error) < 25.0 && !saturated) {
    cumError += error * (SAMPLE_INTERVAL / 1000.0);
  } else {
    cumError = 0; 
  }

  float rateError = (error - lastError) / (SAMPLE_INTERVAL / 1000.0);
  pidOutput = (Kp * error) + (Ki * cumError) + (Kd * rateError);

  // Constraints
  pidOutput = constrain(pidOutput, 0, MAX_DUTY);
  lastError = error;
}

void executeHeaterPWM(unsigned long now) {
  if (now - windowStartTime >= PWM_WINDOW_SIZE) {
    windowStartTime = now;
  }

  unsigned long onTime = (pidOutput / 100.0) * PWM_WINDOW_SIZE;
  
  if (ironEnabled && (now - windowStartTime < onTime)) {
    digitalWrite(PIN_MOSFET, HIGH);
  } else {
    digitalWrite(PIN_MOSFET, LOW);
  }
}

void shutdownHeater() {
  ironEnabled = false;
  pidOutput = 0;
  cumError = 0;
  digitalWrite(PIN_MOSFET, LOW);
}

void updateStatusLED(unsigned long now) {
  if (now >= ledOffTime) {
    digitalWrite(PIN_LED, LOW);
  }
}
