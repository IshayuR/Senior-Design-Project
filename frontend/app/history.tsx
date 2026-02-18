import { View, Text, StyleSheet, ScrollView, Pressable } from "react-native";
import BottomNav from "./BottomNav";
import { useLighting } from "../lightingStore";

const BG = "#DEEAD9";

export default function HistoryScreen() {
  const { history, refreshHistory, loading } = useLighting();

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>History / Log</Text>
        {history.length > 0 && (
          <Pressable style={styles.clearButton} onPress={() => void refreshHistory()}>
            <Text style={styles.clearButtonText}>{loading ? "Refreshing..." : "Refresh log"}</Text>
          </Pressable>
        )}
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {history.length === 0 ? (
          <Text style={styles.emptyText}>No events yet. Toggle the light on the dashboard to see history.</Text>
        ) : (
          history.map((entry) => (
            <View key={entry.id} style={styles.pill}>
              <Text style={styles.pillText}>
                {new Date(entry.timestamp).toLocaleDateString()} •{" "}
                {new Date(entry.timestamp).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} :{" "}
                {entry.action}
              </Text>
            </View>
          ))
        )}
      </ScrollView>

      <BottomNav />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: BG },
  headerRow: {
    paddingTop: 60,
    paddingHorizontal: 24,
    paddingBottom: 8,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  scrollContent: { paddingHorizontal: 24, paddingBottom: 24 },
  title: { fontSize: 24, fontWeight: "700" },
  clearButton: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: "#F1F4EB",
    borderWidth: 1,
    borderColor: "#C1CEB7",
  },
  clearButtonText: { fontSize: 12, fontWeight: "600" },
  emptyText: { fontSize: 15, marginTop: 8 },
  pill: {
    backgroundColor: "#89c756ff",
    borderRadius: 999,
    paddingVertical: 10,
    paddingHorizontal: 18,
    marginBottom: 10,
  },
  pillText: { color: "white", fontWeight: "600", fontSize: 15 },
});
