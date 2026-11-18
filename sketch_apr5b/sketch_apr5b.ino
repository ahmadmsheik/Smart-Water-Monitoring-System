// esp 8266 side code

#include <ArduinoJson.h>
#include <SoftwareSerial.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include "secrets.h"

SoftwareSerial nodemcu(D6, D5); // Rx = D6 AND Tx = D5

unsigned long previousMillis = 0;
unsigned long currentMillis;
const unsigned long period = 10000;  

void setup() {
    
  Serial.begin(9600);
  nodemcu.begin(9600);
  while (!Serial) continue;


    // Connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected, IP address: ");
  Serial.println(WiFi.localIP());

}

void loop() {

 if(nodemcu.available()){

  StaticJsonDocument<1000> doc;
  DeserializationError error = deserializeJson(doc, nodemcu);

  // Test parsing
  if (error) {
      Serial.print("Invalid JSON: ");
      Serial.println(error.c_str());
      return;
    }

  Serial.println("JSON Object Recieved");
  String sensor_id = doc["sensor_id"];
  float flow = doc["FlowRate"];
  float total = doc["Total"];
  Serial.print("Sensor id:  ");
  Serial.println(sensor_id);
  Serial.print("flow rate:  ");
  Serial.println(flow);
  Serial.print("total millileters:  ");
  Serial.println(total);
  Serial.println("-----------------------------------------");

  // Send data to server
    if (WiFi.status() == WL_CONNECTED) {
      WiFiClient client;
      HTTPClient http;
      
      // Prepare JSON payload
      JsonDocument postData;
      postData["sensor_id"] = sensor_id;
      postData["flow_rate"] = flow;
      postData["total"] = total;
      // Add any additional fields you need

      // Start HTTP connection
      http.begin(client, SERVER_URL);
      http.addHeader("Content-Type", "application/json");
      
      // Serialize JSON to string
      String requestBody;
      serializeJson(postData, requestBody);
      
      // Send HTTP POST request
      int httpResponseCode = http.POST(requestBody);
      
      if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println(httpResponseCode);
        Serial.println(response);
      } else {
        Serial.print("Error on sending POST: ");
        Serial.println(httpResponseCode);
      }
      
      http.end();
    } else {
      Serial.println("WiFi Disconnected");
    }
 }
}