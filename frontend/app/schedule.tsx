import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, Alert, Modal } from "react-native";
import { useFocusEffect } from "expo-router";
import BottomNav from "./BottomNav";
import { useLighting } from "../lightingStore";

const BG = "#DEEAD9";

type DaySchedule = {
  id: string;
  label: string;
  enabled: boolean;
  start: string;
  stop: string;
};

type SpecificDateEntry = {
  id: string;
  date: string; // MM-DD-YYYY
  start: string; // HH:MM 24h
  stop: string;
};

const initialDays: DaySchedule[] = [
  { id: "sun", label: "SUN", enabled: false, start: "18:00", stop: "23:30" },
  { id: "mon", label: "MON", enabled: false, start: "18:00", stop: "23:30" },
  { id: "tue", label: "TUES", enabled: false, start: "18:00", stop: "23:30" },
  { id: "wed", label: "WED", enabled: false, start: "18:00", stop: "23:30" },
  { id: "thu", label: "THURS", enabled: false, start: "18:00", stop: "23:30" },
  { id: "fri", label: "FRI", enabled: false, start: "18:00", stop: "23:30" },
  { id: "sat", label: "SAT", enabled: false, start: "18:00", stop: "23:30" },
];

let specificDateIdCounter = 0;
function nextSpecificDateId() {
  specificDateIdCounter += 1;
  return `specific-${specificDateIdCounter}`;
}

const DAY_ID_TO_BACKEND: Record<string, number> = {
  mon: 0,
  tue: 1,
  wed: 2,
  thu: 3,
  fri: 4,
  sat: 5,
  sun: 6,
};

const BACKEND_TO_DAY_ID: Record<number, string> = {
  0: "mon",
  1: "tue",
  2: "wed",
  3: "thu",
  4: "fri",
  5: "sat",
  6: "sun",
};

/** Format date as MM-DD-YYYY */
function formatMonthDayYear(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const y = d.getFullYear();
  return `${m}-${day}-${y}`;
}

type ScheduleTab = "weekly" | "custom";

const US_TIME_ZONE_OPTIONS = [
  { label: "Samoa (SST)", value: "SST" },
  { label: "Hawaii-Aleutian (HST)", value: "HST" },
  { label: "Alaska (AKST)", value: "AKST" },
  { label: "Pacific (PST)", value: "PST" },
  { label: "Mountain (MST)", value: "MST" },
  { label: "Mountain - Arizona (MST)", value: "MST (AZ)" },
  { label: "Central (CST)", value: "CST" },
  { label: "Eastern (EST)", value: "EST" },
  { label: "Atlantic (AST)", value: "AST" },
  { label: "Chamorro (ChST)", value: "CHST" },
];

export default function ScheduleScreen() {
  const [activeTab, setActiveTab] = useState<ScheduleTab>("weekly");
  const [timeZone, setTimeZone] = useState<string>("EST");
  const [timeZoneDropdownOpen, setTimeZoneDropdownOpen] = useState(false);
  const [days, setDays] = useState<DaySchedule[]>(initialDays);
  const [specificDates, setSpecificDates] = useState<SpecificDateEntry[]>([]);
  const { saveWeeklySchedule, saveCustomSchedule, fetchWeeklySchedule, fetchCustomSchedule, loading } = useLighting();

  useFocusEffect(
    useCallback(() => {
      let active = true;

      const loadSchedules = async () => {
        try {
          const [weeklyDays, customDates] = await Promise.all([
            fetchWeeklySchedule(),
            fetchCustomSchedule(),
          ]);

          if (!active) {
            return;
          }

          const weeklyById = new Map(
            weeklyDays.map((day) => [BACKEND_TO_DAY_ID[day.dayOfWeek], day] as const)
          );

          setDays(
            initialDays.map((day) => {
              const saved = weeklyById.get(day.id);
              return saved
                ? { ...day, enabled: saved.enabled, start: saved.start, stop: saved.stop }
                : day;
            })
          );

          setSpecificDates(
            customDates.map((entry) => {
              const [yyyy, mm, dd] = entry.date.split("-");
              return {
                id: nextSpecificDateId(),
                date: `${mm}-${dd}-${yyyy}`,
                start: entry.start,
                stop: entry.stop,
              };
            })
          );
        } catch {
          if (active) {
            // Keep the screen usable even if schedule hydration fails.
          }
        }
      };

      void loadSchedules();

      return () => {
        active = false;
      };
    }, [fetchCustomSchedule, fetchWeeklySchedule])
  );

  const toggleDay = (id: string) => {
    setDays((prev: DaySchedule[]) => prev.map((d) => (d.id === id ? { ...d, enabled: !d.enabled } : d)));
  };

  const updateTime = (id: string, field: "start" | "stop", value: string) => {
    setDays((prev: DaySchedule[]) => prev.map((d) => (d.id === id ? { ...d, [field]: value } : d)));
  };

  const onApplySchedule = async () => {
    try {
      // Map UI days (SUN..SAT) to backend weekday indices (0=Monday..6=Sunday)
      const backendDays = days.map((d) => {
        return {
          dayOfWeek: DAY_ID_TO_BACKEND[d.id] ?? 6,
          enabled: d.enabled,
          start: d.start,
          stop: d.stop,
        };
      });
      await saveWeeklySchedule(backendDays);
      const reloaded = await fetchWeeklySchedule();
      const weeklyById = new Map(
        reloaded.map((day) => [BACKEND_TO_DAY_ID[day.dayOfWeek], day] as const)
      );
      setDays(
        initialDays.map((day) => {
          const saved = weeklyById.get(day.id);
          return saved
            ? { ...day, enabled: saved.enabled, start: saved.start, stop: saved.stop }
            : day;
        })
      );
      Alert.alert("Saved", `Weekly schedule updated (${timeZone}).`);
    } catch (err) {
      Alert.alert("Error", err instanceof Error ? err.message : "Failed to save schedule");
    }
  };

  const addSpecificDate = () => {
    setSpecificDates((prev: SpecificDateEntry[]) => [
      ...prev,
      {
        id: nextSpecificDateId(),
        date: formatMonthDayYear(new Date()),
        start: "01:00",
        stop: "21:00",
      },
    ]);
  };

  const updateSpecificDate = (id: string, field: keyof SpecificDateEntry, value: string) => {
    setSpecificDates((prev: SpecificDateEntry[]) =>
      prev.map((e) => (e.id === id ? { ...e, [field]: value } : e))
    );
  };

  const removeSpecificDate = (id: string) => {
    setSpecificDates((prev: SpecificDateEntry[]) => prev.filter((e) => e.id !== id));
  };

  const onSaveSpecificDates = async () => {
    try {
      const payload = specificDates.map((e) => {
        // Convert MM-DD-YYYY to YYYY-MM-DD for backend
        const [mm, dd, yyyy] = e.date.split("-");
        const isoDate = `${yyyy}-${mm}-${dd}`;
        return {
          date: isoDate,
          start: e.start,
          stop: e.stop,
        };
      });
      await saveCustomSchedule(payload);
      const reloaded = await fetchCustomSchedule();
      setSpecificDates(
        reloaded.map((entry) => {
          const [yyyy, mm, dd] = entry.date.split("-");
          return {
            id: nextSpecificDateId(),
            date: `${mm}-${dd}-${yyyy}`,
            start: entry.start,
            stop: entry.stop,
          };
        })
      );
      Alert.alert("Saved", "Custom dates updated. These override the weekly schedule when dates match.");
    } catch (err) {
      Alert.alert("Error", err instanceof Error ? err.message : "Failed to save custom dates");
    }
  };

  return (
    <View style={styles.screen}>
      <View style={styles.tabBar}>
        <Pressable
          onPress={() => setActiveTab("weekly")}
          style={[styles.tab, activeTab === "weekly" && styles.tabActive]}
        >
          <Text style={[styles.tabText, activeTab === "weekly" && styles.tabTextActive]}>
            Weekly schedule
          </Text>
        </Pressable>
        <Pressable
          onPress={() => setActiveTab("custom")}
          style={[styles.tab, activeTab === "custom" && styles.tabActive]}
        >
          <Text style={[styles.tabText, activeTab === "custom" && styles.tabTextActive]}>
            Custom dates
          </Text>
        </Pressable>
      </View>

      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.timeZoneCard}>
          <Text style={styles.timeZoneTitle}>Time zone</Text>
          <Text style={styles.timeZoneSubtitle}>Choose your U.S. time zone.</Text>
          <Pressable style={styles.dropdownButton} onPress={() => setTimeZoneDropdownOpen(true)}>
            <Text style={styles.dropdownButtonText}>{timeZone}</Text>
            <Text style={styles.dropdownChevron}>▼</Text>
          </Pressable>
        </View>

        {activeTab === "weekly" && (
          <>
            <Text style={styles.title}>Weekly schedule</Text>
            <Text style={styles.subtitle}>
              Choose which days follow a schedule and set automatic on / off times for your lights.
            </Text>

            {days.map((day: DaySchedule) => (
              <View key={day.id} style={[styles.dayCard, day.enabled && styles.dayCardActive]}>
                <View style={styles.dayHeaderRow}>
                  <Text style={styles.dayLabel}>{day.label}</Text>
                  <Pressable
                    onPress={() => toggleDay(day.id)}
                    style={[styles.toggleTrack, day.enabled && styles.toggleTrackOn]}
                  >
                    <View style={[styles.toggleThumb, day.enabled && styles.toggleThumbOn]} />
                  </Pressable>
                </View>

                <View style={styles.timeRow}>
                  <Text style={styles.timeLabel}>Start</Text>
                  <TextInput
                    value={day.start}
                    onChangeText={(text) => updateTime(day.id, "start", text)}
                    style={styles.timeInput}
                    keyboardType="numbers-and-punctuation"
                    placeholder="18:00"
                    placeholderTextColor="#8A9585"
                  />
                </View>

                <View style={styles.timeRow}>
                  <Text style={styles.timeLabel}>Stop</Text>
                  <TextInput
                    value={day.stop}
                    onChangeText={(text) => updateTime(day.id, "stop", text)}
                    style={styles.timeInput}
                    keyboardType="numbers-and-punctuation"
                    placeholder="23:30"
                    placeholderTextColor="#8A9585"
                  />
                </View>
              </View>
            ))}

            <Pressable
              onPress={() => void onApplySchedule()}
              style={[styles.applyButton, loading && styles.applyButtonDisabled]}
              disabled={loading}
            >
              <Text style={styles.applyButtonText}>
                {loading ? "Saving..." : "Apply weekly schedule"}
              </Text>
            </Pressable>

            <View style={styles.helperTextBox}>
              <Text style={styles.helperTitle}>How this schedule works</Text>
              <Text style={styles.helperText}>
                When a day is turned on, your restaurant's exterior lights will automatically follow
                the start and stop times you set here, unless you manually override them from the
                dashboard.
              </Text>
            </View>
          </>
        )}

        {activeTab === "custom" && (
          <>
            <Text style={styles.title}>Custom dates</Text>
            <Text style={styles.subtitle}>
              Set lights on/off for specific dates (e.g. March 19th, 1:00 AM – 9:00 PM).
            </Text>

            {specificDates.map((entry: SpecificDateEntry) => (
              <View key={entry.id} style={styles.specificDateCard}>
                <View style={styles.specificDateHeader}>
                  <Text style={styles.specificDateLabel}>Date & time</Text>
                  <Pressable
                    onPress={() => removeSpecificDate(entry.id)}
                    style={styles.removeButton}
                    hitSlop={8}
                  >
                    <Text style={styles.removeButtonText}>Remove</Text>
                  </Pressable>
                </View>
                <View style={styles.timeRow}>
                  <Text style={styles.timeLabel}>Date</Text>
                  <TextInput
                    value={entry.date}
                    onChangeText={(text) => updateSpecificDate(entry.id, "date", text)}
                    style={styles.timeInput}
                    placeholder="MM-DD-YYYY (e.g. 03-19-2025)"
                    placeholderTextColor="#8A9585"
                  />
                </View>
                <View style={styles.timeRow}>
                  <Text style={styles.timeLabel}>On at</Text>
                  <TextInput
                    value={entry.start}
                    onChangeText={(text) => updateSpecificDate(entry.id, "start", text)}
                    style={styles.timeInput}
                    keyboardType="numbers-and-punctuation"
                    placeholder="01:00"
                    placeholderTextColor="#8A9585"
                  />
                </View>
                <View style={styles.timeRow}>
                  <Text style={styles.timeLabel}>Off at</Text>
                  <TextInput
                    value={entry.stop}
                    onChangeText={(text) => updateSpecificDate(entry.id, "stop", text)}
                    style={styles.timeInput}
                    keyboardType="numbers-and-punctuation"
                    placeholder="21:00"
                    placeholderTextColor="#8A9585"
                  />
                </View>
              </View>
            ))}

            <Pressable onPress={addSpecificDate} style={styles.addDateButton}>
              <Text style={styles.addDateButtonText}>+ Add specific date</Text>
            </Pressable>

            {specificDates.length > 0 && (
              <Pressable onPress={() => void onSaveSpecificDates()} style={styles.applyButton}>
                <Text style={styles.applyButtonText}>Save specific dates</Text>
              </Pressable>
            )}
          </>
        )}
      </ScrollView>

      <Modal
        transparent
        visible={timeZoneDropdownOpen}
        animationType="fade"
        onRequestClose={() => setTimeZoneDropdownOpen(false)}
      >
        <Pressable style={styles.modalBackdrop} onPress={() => setTimeZoneDropdownOpen(false)}>
          <Pressable style={styles.dropdownModalCard} onPress={() => undefined}>
            <Text style={styles.dropdownModalTitle}>Select time zone</Text>
            <ScrollView style={styles.dropdownOptionsScroll} showsVerticalScrollIndicator={false}>
              {US_TIME_ZONE_OPTIONS.map((option) => (
                <Pressable
                  key={option.label}
                  style={[styles.dropdownOption, timeZone === option.value && styles.dropdownOptionActive]}
                  onPress={() => {
                    setTimeZone(option.value);
                    setTimeZoneDropdownOpen(false);
                  }}
                >
                  <Text style={styles.dropdownOptionLabel}>{option.label}</Text>
                  <Text style={styles.dropdownOptionValue}>{option.value}</Text>
                </Pressable>
              ))}
            </ScrollView>
          </Pressable>
        </Pressable>
      </Modal>

      <BottomNav />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: BG,
  },
  tabBar: {
    flexDirection: "row",
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 8,
    gap: 8,
    backgroundColor: BG,
    borderBottomWidth: 1,
    borderBottomColor: "#D6E0D1",
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#E5EBE3",
    borderWidth: 1,
    borderColor: "#D6E0D1",
  },
  tabActive: {
    backgroundColor: "#3B6D31",
    borderColor: "#2d5526",
  },
  tabText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#5F6E5A",
  },
  tabTextActive: {
    color: "#FFFFFF",
  },
  container: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: "800",
    color: "#1F261E",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: "#5F6E5A",
    marginBottom: 18,
  },
  timeZoneCard: {
    backgroundColor: "#F2F7EF",
    borderRadius: 18,
    paddingHorizontal: 18,
    paddingVertical: 14,
    marginBottom: 18,
    borderWidth: 1,
    borderColor: "#DEE7D7",
  },
  timeZoneTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F261E",
    marginBottom: 4,
  },
  timeZoneSubtitle: {
    fontSize: 13,
    color: "#5F6E5A",
    marginBottom: 10,
  },
  dropdownButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: "#D6E0D1",
  },
  dropdownButtonText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#273024",
  },
  dropdownChevron: {
    fontSize: 12,
    color: "#5F6E5A",
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.25)",
    justifyContent: "center",
    paddingHorizontal: 20,
  },
  dropdownModalCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 14,
    maxHeight: "70%",
  },
  dropdownModalTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F261E",
    marginBottom: 10,
  },
  dropdownOptionsScroll: {
    maxHeight: 360,
  },
  dropdownOption: {
    paddingVertical: 10,
    paddingHorizontal: 10,
    borderRadius: 10,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  dropdownOptionActive: {
    backgroundColor: "#ECF4E7",
  },
  dropdownOptionLabel: {
    fontSize: 14,
    color: "#273024",
    flex: 1,
    marginRight: 8,
  },
  dropdownOptionValue: {
    fontSize: 13,
    fontWeight: "700",
    color: "#3B6D31",
  },
  dayCard: {
    backgroundColor: "#F2F7EF",
    borderRadius: 18,
    paddingHorizontal: 18,
    paddingVertical: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "#DEE7D7",
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 5,
    elevation: 2,
  },
  dayCardActive: {
    borderColor: "#9DBE8E",
    backgroundColor: "#E7F2E0",
  },
  dayHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  dayLabel: {
    fontSize: 18,
    fontWeight: "700",
    color: "#1F261E",
  },
  toggleTrack: {
    width: 46,
    height: 26,
    borderRadius: 13,
    backgroundColor: "#D1D8CF",
    padding: 3,
    justifyContent: "center",
  },
  toggleTrackOn: {
    backgroundColor: "#9BC87F",
  },
  toggleThumb: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: "#FFFFFF",
    alignSelf: "flex-start",
  },
  toggleThumbOn: {
    alignSelf: "flex-end",
  },
  timeRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 8,
  },
  timeLabel: {
    width: 52,
    fontSize: 14,
    fontWeight: "600",
    color: "#324131",
  },
  timeInput: {
    flex: 1,
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    paddingVertical: 8,
    paddingHorizontal: 12,
    fontSize: 14,
    color: "#273024",
    borderWidth: 1,
    borderColor: "#D6E0D1",
  },
  applyButton: {
    marginTop: 4,
    marginBottom: 12,
    backgroundColor: "#3B6D31",
    borderRadius: 999,
    paddingVertical: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  applyButtonDisabled: {
    opacity: 0.7,
  },
  applyButtonText: {
    color: "white",
    fontWeight: "700",
    fontSize: 15,
  },
  helperTextBox: {
    marginTop: 12,
    padding: 12,
    borderRadius: 14,
    backgroundColor: "#ECF4E7",
  },
  helperTitle: {
    fontSize: 14,
    fontWeight: "700",
    marginBottom: 4,
    color: "#273024",
  },
  helperText: {
    fontSize: 13,
    color: "#5F6E5A",
    lineHeight: 18,
  },
  specificDateCard: {
    backgroundColor: "#F2F7EF",
    borderRadius: 18,
    paddingHorizontal: 18,
    paddingVertical: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "#DEE7D7",
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 5,
    elevation: 2,
  },
  specificDateHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  specificDateLabel: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1F261E",
  },
  removeButton: {
    paddingVertical: 4,
    paddingHorizontal: 8,
  },
  removeButtonText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#C44",
  },
  addDateButton: {
    marginTop: 4,
    marginBottom: 12,
    backgroundColor: "transparent",
    borderRadius: 999,
    paddingVertical: 12,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: "#3B6D31",
    borderStyle: "dashed",
  },
  addDateButtonText: {
    color: "#3B6D31",
    fontWeight: "700",
    fontSize: 15,
  },
});
