// arduino code

#include <ArduinoJson.h>
#include <SoftwareSerial.h>

SoftwareSerial nodemcu(5, 6); // Rx = 5 and Tx = 6
int flowsensor = 2;
volatile int flow_frequency; // Measures flow sensor pulses
unsigned int l_hour; // Calculated litres/hour
unsigned long currentTime;
unsigned long cloopTime;
unsigned long totalMillilitres;
float flowRate; // Flow rate in L/min

void flow() {
   flow_frequency++;
}

void setup() {
  pinMode(flowsensor, INPUT);
  digitalWrite(flowsensor, HIGH); 
  Serial.begin(9600);  // Initialize hardware UART
  nodemcu.begin(9600);

//  It tells the Arduino to immediately pause whatever it’s doing and run a specific function
// (interrupt handler) when a signal change happens on a pin.
  attachInterrupt(digitalPinToInterrupt(flowsensor), flow, RISING); // Setup Interrupt

  currentTime = millis();
  cloopTime = currentTime;
  totalMillilitres = 0;

  delay(1000);
  Serial.println("program started");
}

void loop() {
  
  StaticJsonDocument<1000> doc;

  currentTime = millis();

  // Every second, calculate and print flow rate and total millilitres
  if (currentTime >= (cloopTime + 1000)) {
    cloopTime = currentTime; // Update cloopTime

    // Calculate flow rate in L/min
    // Formula: (Pulse frequency / 7.5) = flow rate in L/min
    flowRate = (flow_frequency / 7.5);

    // Calculate total millilitres consumed
    totalMillilitres += (flowRate * 1000 / 60); // Convert L/min to mL/s and add to total

    doc["sensor_id"] = "3";
    doc["FlowRate"] = flowRate;
    doc["Total"] = totalMillilitres;
    // Print flow rate and total millilitres
    Serial.print("Flow Rate: ");
    Serial.print(flowRate);
    Serial.print(" L/min \t");

    Serial.print("Total Millilitres: ");
    Serial.print(totalMillilitres);
    Serial.println(" mL");
    serializeJson(doc, nodemcu);
    flow_frequency = 0; // Reset pulse counter
  }
  nodemcu.println(); // Add newline for easier parsing
  delay(1000); // Slow down to 1 second intervals
}