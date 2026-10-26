#include <Arduino.h>

#include "lcd_controller.h"

LcdController lcd;

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(25);
  Serial.println("Lantern LCD diagnostic mode");
  Serial.println("No relay, I2S, Wi-Fi, HTTP, ASR, or voice pipeline is started.");

  if (lcd.begin()) {
    lcd.showText("LANTERN TEST", "LCD READY");
    Serial.printf("LCD READY address=0x%02X\n", lcd.address());
  } else {
    Serial.println("LCD INIT ERROR: check power, SDA/SCL, pull-ups, and contrast");
  }
}

void loop() {
  lcd.tick();
  delay(1000);
}
