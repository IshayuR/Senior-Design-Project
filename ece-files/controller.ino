#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <time.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <strings.h>
#include <Wire.h>
#include <math.h>
#include "certs.h"
#include "controller.h"

const char* AP_SSID = "LightController_Setup";
const char* AP_PASS = "setup1234";

const char* AWS_ENDPOINT = "a34pq72gp9sk70-ats.iot.us-east-1.amazonaws.com";
const char* CLIENT_ID    = "ESP32_Device_01";

const char* TOPIC_CMD    = "esp32/ESP32_Device_01/cmd";
const char* TOPIC_SCHED  = "esp32/ESP32_Device_01/schedule";
const char* TOPIC_PUB    = "esp32/ESP32_Device_01/tele";
const char* TOPIC_STATUS = "esp32/ESP32_Device_01/status";

const char* TZ_STRING = "EST5EDT,M3.2.0/2,M11.1.0/2";

const unsigned long ADS_CONV_TIME_US = 1500;
const unsigned long DEMO_TOGGLE_MS = 7000;
const unsigned long RMS_WINDOW_MS = 1000;
const unsigned long WIFI_CONNECT_TIMEOUT_MS = 15000;
const unsigned long TELE_INTERVAL_MS = 5000;
const unsigned long MQTT_RECONNECT_INTERVAL_MS = 5000;

MeasurementState meas = {
  ADC_IDLE,
  0,
  0,
  0.0f,
  0.0f,
  0,
  0,
  0.0f,
  0.0f,
  0.0f,
  0.0f,
  0.0f,
  0.0f,
  0.0f,
  0.0f
};

ControlState ctrl = {
  false,
  0,
  false,
  {
    {false, 0, 0},
    {false, 0, 0},
    {false, 0, 0},
    {false, 0, 0},
    {false, 0, 0},
    {false, 0, 0}
  },
  false,
  false
};

RuntimeState runState = {
  PROVISIONING,
  0,
  0,
  false,
  false,
  0,
  0
};

WifiState wifiState = {
  "",
  ""
};

ScheduleStore scheduleStore;
int activeScheduleDate = 0;

WiFiClientSecure net;
PubSubClient mqtt(net);
WebServer server(80);
Preferences prefs;

bool loadWiFiCreds();
void saveWiFiCreds(const String& ssid, const String& pass);
void clearWiFiCreds();
void checkResetButton();
String htmlPage();
void startProvisioningMode();
bool connectWiFi();
void serviceWiFiReconnect();
void syncTime();
void publishStatus(const char* statusMsg);
void connectAWS();
void onMessage(char* topic, byte* payload, unsigned int len);

void loadScheduleStore();
void saveScheduleStore();
void clearScheduleStore();
bool validDate(int date);
int getTodayDate();
int findDateScheduleIndex(int date);
int findFreeScheduleIndex();
int getSlotForDate(int date);
void clearActiveScheduleBlocks();
void applyScheduleForToday(bool force);
bool parseAndSaveDatedSchedule(const char* msg);

void startADS1115Conversion(uint8_t muxBits);
int16_t readADS1115Result();
float rawToVoltage(int16_t raw);
float correctVoltageA0(float adcVoltage);
float correctVoltageA1(float adcVoltage);
float getCurrentInstant(float a0);
float getHVINInstant(float a1);
void serviceADS1115();

float readVoltage();
float readCurrent();

void checkSchedule();
void publishTelemetry();
void updateStatusLed();

bool loadWiFiCreds() {
  prefs.begin("wifi", true);
  wifiState.ssid = prefs.getString("ssid", "");
  wifiState.pass = prefs.getString("pass", "");
  prefs.end();
  return wifiState.ssid.length() > 0;
}

void saveWiFiCreds(const String& ssid, const String& pass) {
  prefs.begin("wifi", false);
  prefs.putString("ssid", ssid);
  prefs.putString("pass", pass);
  prefs.end();
}

void clearWiFiCreds() {
  prefs.begin("wifi", false);
  prefs.clear();
  prefs.end();
}

void checkResetButton() {
  static unsigned long pressStart = 0;
  static bool wasPressed = false;
  static bool resetTriggered = false;

  bool pressed = (digitalRead(RESET_BUTTON_PIN) == LOW);

  if (pressed && !wasPressed) {
    pressStart = millis();
    wasPressed = true;
    resetTriggered = false;
  }

  if (!pressed) {
    wasPressed = false;
    pressStart = 0;
    resetTriggered = false;
    return;
  }

  if (!resetTriggered && millis() - pressStart >= 3000) {
    resetTriggered = true;
    Serial.println("Resetting WiFi credentials");
    clearWiFiCreds();
    delay(200);
    ESP.restart();
  }
}

String htmlPage() {
  String page;
  page += "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
  page += "<title>WiFi Setup</title></head><body>";
  page += "<h2>ESP32 Lighting Controller Setup</h2>";
  page += "<p>Connect this device to local WiFi.</p>";
  page += "<form action='/save' method='POST'>";
  page += "SSID:<br><input name='ssid'><br><br>";
  page += "Password:<br><input name='pass' type='password'><br><br>";
  page += "<input type='submit' value='Save'>";
  page += "</form>";
  page += "<br><form action='/clear' method='POST'><input type='submit' value='Clear Saved WiFi'></form>";
  page += "</body></html>";
  return page;
}

void startProvisioningMode() {
  runState.deviceState = PROVISIONING;

  mqtt.disconnect();
  WiFi.disconnect(true, true);
  delay(500);

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);

  server.stop();

  server.on("/", HTTP_GET, []() {
    server.send(200, "text/html", htmlPage());
  });

  server.on("/save", HTTP_POST, []() {
    String ssid = server.arg("ssid");
    String pass = server.arg("pass");

    if (ssid.length() == 0) {
      server.send(400, "text/html", "<html><body><h3>SSID cannot be empty.</h3><a href='/'>Back</a></body></html>");
      return;
    }

    saveWiFiCreds(ssid, pass);
    server.send(200, "text/html", "<html><body><h3>Saved. Rebooting...</h3></body></html>");
    delay(1500);
    ESP.restart();
  });

  server.on("/clear", HTTP_POST, []() {
    clearWiFiCreds();
    server.send(200, "text/html", "<html><body><h3>Saved WiFi cleared. Rebooting...</h3></body></html>");
    delay(1500);
    ESP.restart();
  });

  server.begin();
}

bool connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(wifiState.ssid.c_str(), wifiState.pass.c_str());

  Serial.print("Connecting to WiFi");

  unsigned long start = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected, IP: ");
    Serial.println(WiFi.localIP());
    return true;
  }

  Serial.println("WiFi connection FAILED");
  return false;
}

void serviceWiFiReconnect() {
  if (WiFi.status() == WL_CONNECTED) {
    if (runState.wifiReconnectInProgress) {
      runState.wifiReconnectInProgress = false;
      Serial.print("WiFi reconnected, IP: ");
      Serial.println(WiFi.localIP());
      syncTime();
      activeScheduleDate = 0;
    }
    return;
  }

  if (!runState.wifiReconnectInProgress) {
    if (millis() - runState.lastWifiReconnectAttemptMs >= 5000) {
      runState.lastWifiReconnectAttemptMs = millis();
      runState.wifiReconnectInProgress = true;
      runState.wifiReconnectStartMs = millis();

      WiFi.disconnect();
      WiFi.mode(WIFI_STA);
      WiFi.begin(wifiState.ssid.c_str(), wifiState.pass.c_str());

      Serial.println("WiFi reconnect started");
    }
    return;
  }

  if (millis() - runState.wifiReconnectStartMs >= WIFI_CONNECT_TIMEOUT_MS) {
    runState.wifiReconnectInProgress = false;
    Serial.println("WiFi reconnect attempt timed out");
  }
}

void syncTime() {
  setenv("TZ", TZ_STRING, 1);
  tzset();
  configTzTime(TZ_STRING, "pool.ntp.org", "time.nist.gov", "time.google.com");

  while (time(nullptr) < 1700000000UL) {
    delay(200);
  }
}

void publishStatus(const char* statusMsg) {
  if (!mqtt.connected()) return;

  char msg[256];
  String ip = WiFi.isConnected() ? WiFi.localIP().toString() : "0.0.0.0";

  snprintf(
    msg,
    sizeof(msg),
    "{\"device\":\"%s\",\"status\":\"%s\",\"ip\":\"%s\",\"uptime\":%lu,\"active_date\":%d}",
    CLIENT_ID,
    statusMsg,
    ip.c_str(),
    millis() / 1000UL,
    activeScheduleDate
  );

  mqtt.publish(TOPIC_STATUS, msg);
}

void loadScheduleStore() {
  memset(&scheduleStore, 0, sizeof(scheduleStore));

  prefs.begin("sched", true);
  size_t len = prefs.getBytesLength("store");

  if (len == sizeof(scheduleStore)) {
    prefs.getBytes("store", &scheduleStore, sizeof(scheduleStore));
    Serial.println("Schedule store loaded");
  } else {
    Serial.println("No saved schedule store found");
  }

  prefs.end();
}

void saveScheduleStore() {
  prefs.begin("sched", false);
  prefs.putBytes("store", &scheduleStore, sizeof(scheduleStore));
  prefs.end();
  Serial.println("Schedule store saved");
}

void clearScheduleStore() {
  memset(&scheduleStore, 0, sizeof(scheduleStore));
  prefs.begin("sched", false);
  prefs.clear();
  prefs.end();
  clearActiveScheduleBlocks();
  activeScheduleDate = 0;
}

bool validDate(int date) {
  int year = date / 10000;
  int month = (date / 100) % 100;
  int day = date % 100;

  if (year < 2024 || year > 2099) return false;
  if (month < 1 || month > 12) return false;

  int daysInMonth[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};

  bool leap = ((year % 4 == 0 && year % 100 != 0) || (year % 400 == 0));

  if (leap && month == 2) {
    return day >= 1 && day <= 29;
  }

  return day >= 1 && day <= daysInMonth[month - 1];
}

int getTodayDate() {
  time_t now = time(nullptr);
  struct tm* t = localtime(&now);

  int year = t->tm_year + 1900;
  int month = t->tm_mon + 1;
  int day = t->tm_mday;

  return year * 10000 + month * 100 + day;
}

int findDateScheduleIndex(int date) {
  for (int i = 0; i < MAX_SAVED_DATES; i++) {
    if (scheduleStore.days[i].valid && scheduleStore.days[i].date == date) {
      return i;
    }
  }

  return -1;
}

int findFreeScheduleIndex() {
  for (int i = 0; i < MAX_SAVED_DATES; i++) {
    if (!scheduleStore.days[i].valid) {
      return i;
    }
  }

  return -1;
}

int getSlotForDate(int date) {
  int idx = findDateScheduleIndex(date);
  if (idx >= 0) return idx;

  idx = findFreeScheduleIndex();
  if (idx >= 0) return idx;

  return 0;
}

void clearActiveScheduleBlocks() {
  for (int i = 0; i < MAX_SCHEDULE_BLOCKS; i++) {
    ctrl.scheduleBlocks[i].enabled = false;
    ctrl.scheduleBlocks[i].onMinuteOfDay = 0;
    ctrl.scheduleBlocks[i].offMinuteOfDay = 0;
  }
}

void applyScheduleForToday(bool force) {
  int today = getTodayDate();

  if (!force && activeScheduleDate == today) {
    return;
  }

  activeScheduleDate = today;

  int idx = findDateScheduleIndex(today);

  if (idx < 0) {
    clearActiveScheduleBlocks();
    publishStatus("no_schedule_for_today");
    return;
  }

  for (int i = 0; i < MAX_SCHEDULE_BLOCKS; i++) {
    ctrl.scheduleBlocks[i] = scheduleStore.days[idx].blocks[i];
  }

  publishStatus("daily_schedule_loaded");
}

bool parseAndSaveDatedSchedule(const char* msg) {
  int date;
  int s1_en, s1_start_h, s1_start_m, s1_end_h, s1_end_m;
  int s2_en, s2_start_h, s2_start_m, s2_end_h, s2_end_m;
  int s3_en, s3_start_h, s3_start_m, s3_end_h, s3_end_m;
  int s4_en, s4_start_h, s4_start_m, s4_end_h, s4_end_m;
  int s5_en, s5_start_h, s5_start_m, s5_end_h, s5_end_m;
  int s6_en, s6_start_h, s6_start_m, s6_end_h, s6_end_m;

  int parsed = sscanf(
    msg,
    "{\"date\":%d,\"s1_en\":%d,\"s1_start_h\":%d,\"s1_start_m\":%d,\"s1_end_h\":%d,\"s1_end_m\":%d,"
    "\"s2_en\":%d,\"s2_start_h\":%d,\"s2_start_m\":%d,\"s2_end_h\":%d,\"s2_end_m\":%d,"
    "\"s3_en\":%d,\"s3_start_h\":%d,\"s3_start_m\":%d,\"s3_end_h\":%d,\"s3_end_m\":%d,"
    "\"s4_en\":%d,\"s4_start_h\":%d,\"s4_start_m\":%d,\"s4_end_h\":%d,\"s4_end_m\":%d,"
    "\"s5_en\":%d,\"s5_start_h\":%d,\"s5_start_m\":%d,\"s5_end_h\":%d,\"s5_end_m\":%d,"
    "\"s6_en\":%d,\"s6_start_h\":%d,\"s6_start_m\":%d,\"s6_end_h\":%d,\"s6_end_m\":%d}",
    &date,
    &s1_en, &s1_start_h, &s1_start_m, &s1_end_h, &s1_end_m,
    &s2_en, &s2_start_h, &s2_start_m, &s2_end_h, &s2_end_m,
    &s3_en, &s3_start_h, &s3_start_m, &s3_end_h, &s3_end_m,
    &s4_en, &s4_start_h, &s4_start_m, &s4_end_h, &s4_end_m,
    &s5_en, &s5_start_h, &s5_start_m, &s5_end_h, &s5_end_m,
    &s6_en, &s6_start_h, &s6_start_m, &s6_end_h, &s6_end_m
  );

  if (parsed != 31) {
    publishStatus("schedule_parse_error");
    return false;
  }

  if (!validDate(date)) {
    publishStatus("schedule_invalid_date");
    return false;
  }

  int en[6]   = {s1_en, s2_en, s3_en, s4_en, s5_en, s6_en};
  int onH[6]  = {s1_start_h, s2_start_h, s3_start_h, s4_start_h, s5_start_h, s6_start_h};
  int onM[6]  = {s1_start_m, s2_start_m, s3_start_m, s4_start_m, s5_start_m, s6_start_m};
  int offH[6] = {s1_end_h, s2_end_h, s3_end_h, s4_end_h, s5_end_h, s6_end_h};
  int offM[6] = {s1_end_m, s2_end_m, s3_end_m, s4_end_m, s5_end_m, s6_end_m};

  for (int i = 0; i < MAX_SCHEDULE_BLOCKS; i++) {
    if (!(en[i] == 0 || en[i] == 1)) {
      publishStatus("schedule_invalid_enable");
      return false;
    }

    if (onH[i] < 0 || onH[i] > 23 ||
        offH[i] < 0 || offH[i] > 23 ||
        onM[i] < 0 || onM[i] > 59 ||
        offM[i] < 0 || offM[i] > 59) {
      publishStatus("schedule_invalid_time");
      return false;
    }
  }

  int idx = getSlotForDate(date);

  scheduleStore.days[idx].valid = true;
  scheduleStore.days[idx].date = date;

  for (int i = 0; i < MAX_SCHEDULE_BLOCKS; i++) {
    scheduleStore.days[idx].blocks[i].enabled = (en[i] == 1);
    scheduleStore.days[idx].blocks[i].onMinuteOfDay = onH[i] * 60 + onM[i];
    scheduleStore.days[idx].blocks[i].offMinuteOfDay = offH[i] * 60 + offM[i];
  }

  saveScheduleStore();

  ctrl.manualOverride = false;
  ctrl.demoMode = false;

  if (date == getTodayDate()) {
    applyScheduleForToday(true);
  }

  publishStatus("dated_schedule_updated");
  return true;
}

void onMessage(char* topic, byte* payload, unsigned int len) {
  char msg[1024];

  if (len >= sizeof(msg)) {
    len = sizeof(msg) - 1;
  }

  memcpy(msg, payload, len);
  msg[len] = '\0';

  if (strcmp(topic, TOPIC_CMD) == 0) {
    if (strcasecmp(msg, "ON") == 0) {
      ctrl.manualOverride = true;
      ctrl.demoMode = false;
      ctrl.manualState = true;
      digitalWrite(LOAD_PIN_1, HIGH);
      digitalWrite(LOAD_PIN_2, HIGH);
      publishStatus("manual_on");
    } else if (strcasecmp(msg, "OFF") == 0) {
      ctrl.manualOverride = true;
      ctrl.demoMode = false;
      ctrl.manualState = false;
      digitalWrite(LOAD_PIN_1, LOW);
      digitalWrite(LOAD_PIN_2, LOW);
      publishStatus("manual_off");
    } else if (strcasecmp(msg, "AUTO") == 0) {
      ctrl.manualOverride = false;
      ctrl.demoMode = false;
      applyScheduleForToday(true);
      publishStatus("auto_mode");
    } else if (strcasecmp(msg, "DEMO") == 0) {
      ctrl.manualOverride = false;
      ctrl.demoMode = true;
      ctrl.lastDemoToggleMs = millis();
      ctrl.demoLoadState = false;
      digitalWrite(LOAD_PIN_1, LOW);
      digitalWrite(LOAD_PIN_2, LOW);
      publishStatus("demo_mode");
    } else if (strcasecmp(msg, "CLEAR_SCHEDULES") == 0) {
      clearScheduleStore();
      publishStatus("schedules_cleared");
    }

    return;
  }

  if (strcmp(topic, TOPIC_SCHED) == 0) {
    parseAndSaveDatedSchedule(msg);
    return;
  }
}

void connectAWS() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (mqtt.connected()) return;

  static unsigned long lastMqttAttemptMs = 0;

  if (millis() - lastMqttAttemptMs < MQTT_RECONNECT_INTERVAL_MS) return;

  lastMqttAttemptMs = millis();

  Serial.println("Connecting to AWS...");

  if (mqtt.connect(CLIENT_ID)) {
    Serial.println("AWS Connected!");
    mqtt.subscribe(TOPIC_CMD);
    mqtt.subscribe(TOPIC_SCHED);
    publishStatus("boot");
    publishStatus("online");
    applyScheduleForToday(true);
  } else {
    Serial.print("MQTT failed, rc=");
    Serial.println(mqtt.state());
  }
}

float correctVoltageA0(float adcVoltage) {
  if (adcVoltage < 1.35f) {
    return adcVoltage + 0.0045f;
  } else if (adcVoltage < 1.95f) {
    return adcVoltage + 0.0075f;
  } else {
    return adcVoltage;
  }
}

float correctVoltageA1(float adcVoltage) {
  if (adcVoltage < 1.35f) {
    return adcVoltage + 0.0045f;
  } else if (adcVoltage < 1.95f) {
    return adcVoltage + 0.0075f;
  } else {
    return adcVoltage;
  }
}

void startADS1115Conversion(uint8_t muxBits) {
  uint16_t config = 0;

  config |= (1 << 15);
  config |= (muxBits << 12);
  config |= (1 << 9);
  config |= (1 << 8);
  config |= (7 << 5);
  config |= (3 << 0);

  Wire.beginTransmission(ADS1115_ADDR);
  Wire.write(0x01);
  Wire.write(config >> 8);
  Wire.write(config & 0xFF);
  Wire.endTransmission();
}

int16_t readADS1115Result() {
  Wire.beginTransmission(ADS1115_ADDR);
  Wire.write(0x00);
  Wire.endTransmission();

  Wire.requestFrom(ADS1115_ADDR, (uint8_t)2);

  if (Wire.available() < 2) {
    return 0;
  }

  return (int16_t)((Wire.read() << 8) | Wire.read());
}

float rawToVoltage(int16_t raw) {
  return raw * (4.096f / 32768.0f);
}

float getCurrentInstant(float a0) {
  return (a0 - MID_BIAS) / CURRENT_SENSITIVITY;
}

float getHVINInstant(float a1) {
  return SCALE * (a1 - MID_BIAS);
}

void serviceADS1115() {
  unsigned long nowUs = micros();
  unsigned long nowMs = millis();

  switch (meas.adcState) {
    case ADC_IDLE:
      startADS1115Conversion(4);
      meas.adcStartUs = nowUs;
      meas.adcState = ADC_WAIT_A0;
      break;

    case ADC_WAIT_A0:
      if ((nowUs - meas.adcStartUs) >= ADS_CONV_TIME_US) {
        float a0 = correctVoltageA0(rawToVoltage(readADS1115Result()));
        float current = getCurrentInstant(a0);

        meas.latestCurrentInst = current;
        meas.currentSumSq += current * current;
        meas.currentSamples++;

        float currentAbs = fabs(current);

        if (currentAbs > meas.currentMaxAbs) {
          meas.currentMaxAbs = currentAbs;
        }

        meas.latestCurrentAmp = meas.currentMaxAbs - 0.05f;

        if (meas.latestCurrentAmp < 0.0f) {
          meas.latestCurrentAmp = 0.0f;
        }

        startADS1115Conversion(5);
        meas.adcStartUs = micros();
        meas.adcState = ADC_WAIT_A1;
      }
      break;

    case ADC_WAIT_A1:
      if ((nowUs - meas.adcStartUs) >= ADS_CONV_TIME_US) {
        float a1 = correctVoltageA1(rawToVoltage(readADS1115Result()));
        float voltage = getHVINInstant(a1);

        meas.latestVoltageInst = voltage;
        meas.voltageSumSq += voltage * voltage;
        meas.voltageSamples++;

        float voltageAbs = fabs(voltage);

        if (voltageAbs > meas.voltageMaxAbs) {
          meas.voltageMaxAbs = voltageAbs;
        }

        meas.latestVoltageAmp = meas.voltageMaxAbs - 0.15f;

        if (meas.latestVoltageAmp < 0.0f) {
          meas.latestVoltageAmp = 0.0f;
        }

        startADS1115Conversion(4);
        meas.adcStartUs = micros();
        meas.adcState = ADC_WAIT_A0;
      }
      break;
  }

  if ((nowMs - meas.rmsWindowStartMs) >= RMS_WINDOW_MS) {
    if (meas.currentSamples > 0) {
      meas.latestCurrentRMS = sqrt(meas.currentSumSq / meas.currentSamples);

      if (meas.latestCurrentRMS < 0.0f) {
        meas.latestCurrentRMS = 0.0f;
      }
    }

    if (meas.voltageSamples > 0) {
      meas.latestVoltageRMS = sqrt(meas.voltageSumSq / meas.voltageSamples);

      if (meas.latestVoltageRMS < 0.0f) {
        meas.latestVoltageRMS = 0.0f;
      }
    }

    meas.currentSumSq = 0.0f;
    meas.voltageSumSq = 0.0f;
    meas.currentSamples = 0;
    meas.voltageSamples = 0;
    meas.currentMaxAbs = 0.0f;
    meas.voltageMaxAbs = 0.0f;
    meas.rmsWindowStartMs = nowMs;
  }
}

float readVoltage() {
  return meas.latestVoltageRMS;
}

float readCurrent() {
  return meas.latestCurrentRMS;
}

void checkSchedule() {
  applyScheduleForToday();

  if (ctrl.manualOverride) {
    digitalWrite(LOAD_PIN_1, ctrl.manualState ? HIGH : LOW);
    digitalWrite(LOAD_PIN_2, ctrl.manualState ? HIGH : LOW);
    return;
  }

  if (ctrl.demoMode) {
    if (millis() - ctrl.lastDemoToggleMs >= DEMO_TOGGLE_MS) {
      ctrl.lastDemoToggleMs = millis();
      ctrl.demoLoadState = !ctrl.demoLoadState;
    }

    digitalWrite(LOAD_PIN_1, ctrl.demoLoadState ? HIGH : LOW);
    digitalWrite(LOAD_PIN_2, ctrl.demoLoadState ? HIGH : LOW);
    return;
  }

  time_t now = time(nullptr);
  struct tm* t = localtime(&now);
  int currentMinuteOfDay = t->tm_hour * 60 + t->tm_min;

  bool shouldBeOn = true;

  for (int i = 0; i < MAX_SCHEDULE_BLOCKS; i++) {
    if (!ctrl.scheduleBlocks[i].enabled) continue;

    int onMin = ctrl.scheduleBlocks[i].onMinuteOfDay;
    int offMin = ctrl.scheduleBlocks[i].offMinuteOfDay;

    if (onMin < offMin) {
      if (currentMinuteOfDay >= onMin && currentMinuteOfDay < offMin) {
        shouldBeOn = false;
        break;
      }
    } else if (onMin > offMin) {
      if (currentMinuteOfDay >= onMin || currentMinuteOfDay < offMin) {
        shouldBeOn = false;
        break;
      }
    } else {
      shouldBeOn = false;
      break;
    }
  }

  digitalWrite(LOAD_PIN_1, shouldBeOn ? HIGH : LOW);
  digitalWrite(LOAD_PIN_2, shouldBeOn ? HIGH : LOW);
}

void publishTelemetry() {
  if (!mqtt.connected()) return;
  if (millis() - runState.lastTeleMs < TELE_INTERVAL_MS) return;

  runState.lastTeleMs = millis();

  float voltage = readVoltage();
  float current = readCurrent();
  float power = voltage * current;
  int loadState = digitalRead(LOAD_PIN_1);
  float maxVoltage = meas.latestVoltageAmp;

  char msg[1536];

  snprintf(
    msg,
    sizeof(msg),
    "{\"device\":\"%s\",\"uptime\":%lu,\"active_date\":%d,\"RMSvoltage\":%.2f,\"maxVoltage\":%.2f,\"current\":%.2f,\"power\":%.2f,\"load\":%d,\"mode\":\"%s\",\"schedule_type\":\"off_blocks\","
    "\"s1_en\":%d,\"s1_start_h\":%d,\"s1_start_m\":%d,\"s1_end_h\":%d,\"s1_end_m\":%d,"
    "\"s2_en\":%d,\"s2_start_h\":%d,\"s2_start_m\":%d,\"s2_end_h\":%d,\"s2_end_m\":%d,"
    "\"s3_en\":%d,\"s3_start_h\":%d,\"s3_start_m\":%d,\"s3_end_h\":%d,\"s3_end_m\":%d,"
    "\"s4_en\":%d,\"s4_start_h\":%d,\"s4_start_m\":%d,\"s4_end_h\":%d,\"s4_end_m\":%d,"
    "\"s5_en\":%d,\"s5_start_h\":%d,\"s5_start_m\":%d,\"s5_end_h\":%d,\"s5_end_m\":%d,"
    "\"s6_en\":%d,\"s6_start_h\":%d,\"s6_start_m\":%d,\"s6_end_h\":%d,\"s6_end_m\":%d}",
    CLIENT_ID,
    millis() / 1000UL,
    activeScheduleDate,
    voltage,
    maxVoltage,
    current,
    power,
    loadState,
    ctrl.manualOverride ? "manual" : (ctrl.demoMode ? "demo" : "auto"),

    ctrl.scheduleBlocks[0].enabled ? 1 : 0,
    ctrl.scheduleBlocks[0].onMinuteOfDay / 60,
    ctrl.scheduleBlocks[0].onMinuteOfDay % 60,
    ctrl.scheduleBlocks[0].offMinuteOfDay / 60,
    ctrl.scheduleBlocks[0].offMinuteOfDay % 60,

    ctrl.scheduleBlocks[1].enabled ? 1 : 0,
    ctrl.scheduleBlocks[1].onMinuteOfDay / 60,
    ctrl.scheduleBlocks[1].onMinuteOfDay % 60,
    ctrl.scheduleBlocks[1].offMinuteOfDay / 60,
    ctrl.scheduleBlocks[1].offMinuteOfDay % 60,

    ctrl.scheduleBlocks[2].enabled ? 1 : 0,
    ctrl.scheduleBlocks[2].onMinuteOfDay / 60,
    ctrl.scheduleBlocks[2].onMinuteOfDay % 60,
    ctrl.scheduleBlocks[2].offMinuteOfDay / 60,
    ctrl.scheduleBlocks[2].offMinuteOfDay % 60,

    ctrl.scheduleBlocks[3].enabled ? 1 : 0,
    ctrl.scheduleBlocks[3].onMinuteOfDay / 60,
    ctrl.scheduleBlocks[3].onMinuteOfDay % 60,
    ctrl.scheduleBlocks[3].offMinuteOfDay / 60,
    ctrl.scheduleBlocks[3].offMinuteOfDay % 60,

    ctrl.scheduleBlocks[4].enabled ? 1 : 0,
    ctrl.scheduleBlocks[4].onMinuteOfDay / 60,
    ctrl.scheduleBlocks[4].onMinuteOfDay % 60,
    ctrl.scheduleBlocks[4].offMinuteOfDay / 60,
    ctrl.scheduleBlocks[4].offMinuteOfDay % 60,

    ctrl.scheduleBlocks[5].enabled ? 1 : 0,
    ctrl.scheduleBlocks[5].onMinuteOfDay / 60,
    ctrl.scheduleBlocks[5].onMinuteOfDay % 60,
    ctrl.scheduleBlocks[5].offMinuteOfDay / 60,
    ctrl.scheduleBlocks[5].offMinuteOfDay % 60
  );

  bool ok = mqtt.publish(TOPIC_PUB, msg);
  Serial.println(ok ? "Telemetry SUCCESS" : "Telemetry FAILED");
}

void updateStatusLed() {
  unsigned long interval = (runState.deviceState == PROVISIONING) ? 200 : 1000;

  if (millis() - runState.lastLedMs >= interval) {
    runState.lastLedMs = millis();
    runState.ledState = !runState.ledState;
    digitalWrite(STATUS_LED, runState.ledState ? HIGH : LOW);
  }
}

void setup() {
  Wire.begin(16, 17);
  Wire.setClock(100000);

  meas.rmsWindowStartMs = millis();
  meas.adcState = ADC_IDLE;

  pinMode(LOAD_PIN_1, OUTPUT);
  pinMode(LOAD_PIN_2, OUTPUT);
  pinMode(STATUS_LED, OUTPUT);
  pinMode(RESET_BUTTON_PIN, INPUT_PULLUP);

  digitalWrite(LOAD_PIN_1, LOW);
  digitalWrite(LOAD_PIN_2, LOW);
  digitalWrite(STATUS_LED, LOW);

  Serial.begin(115200);
  analogReadResolution(12);

  mqtt.setBufferSize(1536);

  loadScheduleStore();

  if (!loadWiFiCreds()) {
    startProvisioningMode();
    return;
  }

  if (!connectWiFi()) {
    clearWiFiCreds();
    startProvisioningMode();
    return;
  }

  runState.deviceState = NORMAL_OPERATION;
  syncTime();

  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);

  mqtt.setServer(AWS_ENDPOINT, 8883);
  mqtt.setCallback(onMessage);

  connectAWS();
}

void loop() {
  checkResetButton();
  updateStatusLed();

  if (runState.deviceState == PROVISIONING) {
    server.handleClient();
    delay(10);
    return;
  }

  serviceWiFiReconnect();

  if (WiFi.status() == WL_CONNECTED) {
    if (!mqtt.connected()) {
      connectAWS();
    }

    mqtt.loop();
    publishTelemetry();
  }

  checkSchedule();
  serviceADS1115();
}
