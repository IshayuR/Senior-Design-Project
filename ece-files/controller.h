#ifndef CONTROLLER_H
#define CONTROLLER_H

#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <time.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <Wire.h>

#define ADS1115_ADDR 0x48

#define LOAD_PIN_1 19
#define LOAD_PIN_2 21
#define STATUS_LED 2
#define RESET_BUTTON_PIN 25

#define MID_BIAS 1.65f
#define CURRENT_SENSITIVITY 0.019f
#define SCALE 200.0f

#define MAX_SCHEDULE_BLOCKS 6
#define MAX_SAVED_DATES 31

extern const char* AP_SSID;
extern const char* AP_PASS;

extern const char* AWS_ENDPOINT;
extern const char* CLIENT_ID;

extern const char* TOPIC_CMD;
extern const char* TOPIC_SCHED;
extern const char* TOPIC_PUB;
extern const char* TOPIC_STATUS;

extern const char* TZ_STRING;

extern const unsigned long ADS_CONV_TIME_US;
extern const unsigned long DEMO_TOGGLE_MS;
extern const unsigned long RMS_WINDOW_MS;
extern const unsigned long WIFI_CONNECT_TIMEOUT_MS;
extern const unsigned long TELE_INTERVAL_MS;
extern const unsigned long MQTT_RECONNECT_INTERVAL_MS;

extern const char AWS_CERT_CA[];
extern const char AWS_CERT_CRT[];
extern const char AWS_CERT_PRIVATE[];

enum AdcState {
  ADC_IDLE,
  ADC_WAIT_A0,
  ADC_WAIT_A1
};

enum DeviceState {
  PROVISIONING,
  NORMAL_OPERATION
};

struct MeasurementState {
  AdcState adcState;
  unsigned long adcStartUs;
  unsigned long rmsWindowStartMs;

  float currentSumSq;
  float voltageSumSq;
  uint32_t currentSamples;
  uint32_t voltageSamples;

  float latestCurrentInst;
  float latestVoltageInst;

  float latestCurrentRMS;
  float latestVoltageRMS;

  float currentMaxAbs;
  float voltageMaxAbs;

  float latestCurrentAmp;
  float latestVoltageAmp;
};

struct ScheduleBlock {
  bool enabled;
  int onMinuteOfDay;
  int offMinuteOfDay;
};

struct DateSchedule {
  bool valid;
  int date;
  ScheduleBlock blocks[MAX_SCHEDULE_BLOCKS];
};

struct ScheduleStore {
  DateSchedule days[MAX_SAVED_DATES];
};

struct ControlState {
  bool demoMode;
  unsigned long lastDemoToggleMs;
  bool demoLoadState;

  ScheduleBlock scheduleBlocks[MAX_SCHEDULE_BLOCKS];

  bool manualOverride;
  bool manualState;
};

struct RuntimeState {
  DeviceState deviceState;
  unsigned long lastTeleMs;
  unsigned long lastLedMs;
  bool ledState;

  bool wifiReconnectInProgress;
  unsigned long wifiReconnectStartMs;
  unsigned long lastWifiReconnectAttemptMs;
};

struct WifiState {
  String ssid;
  String pass;
};

extern MeasurementState meas;
extern ControlState ctrl;
extern RuntimeState runState;
extern WifiState wifiState;
extern ScheduleStore scheduleStore;
extern int activeScheduleDate;

extern WiFiClientSecure net;
extern PubSubClient mqtt;
extern WebServer server;
extern Preferences prefs;

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
void applyScheduleForToday(bool force = false);
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

#endif