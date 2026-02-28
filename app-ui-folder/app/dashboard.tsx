import { View, Text, StyleSheet, Pressable } from "react-native";
import { useRouter } from "expo-router";
import { useLighting } from "../lightingStore";
import BottomNav from "./BottomNav";

const BG = "#DEEAD9";
const BULB_SIZE = 150;

export default function DashboardScreen() {
  const { isOn, toggleLight } = useLighting();
  const router = useRouter();

  const bulbColor = isOn ? "#FFF58A" : "#E2E2E2";
  const statusText = isOn ? "On" : "Off";

  return (
    <View style={styles.container}>
      <View style={styles.mainCard}>
        <Text style={styles.restaurantLabel}>name_restaurant status</Text>

        <Pressable style={styles.bulbWrapper} onPress={() => void toggleLight()}>
          {isOn && (
            <>
              <View style={[styles.ray, styles.rayTop]} />
              <View style={[styles.ray, styles.rayLeft]} />
              <View style={[styles.ray, styles.rayRight]} />
              <View style={[styles.ray, styles.rayTopLeft]} />
              <View style={[styles.ray, styles.rayTopRight]} />
              <View style={[styles.ray, styles.rayMiddleBottomLeft]} />
              <View style={[styles.ray, styles.rayMiddleBottomRight]} />
              <View style={[styles.ray, styles.rayBottomLeft]} />
              <View style={[styles.ray, styles.rayBottomRight]} />
            </>
          )}

          <View style={[styles.bulbCircle, { backgroundColor: bulbColor }]} />
          <View style={[styles.bulbNeck, { backgroundColor: bulbColor }]} />
          <View style={[styles.baseBar, { backgroundColor: bulbColor }]} />
          <View style={[styles.baseBar, { backgroundColor: bulbColor }]} />
          <View style={[styles.baseBar, { backgroundColor: bulbColor }]} />
        </Pressable>

        <Text style={styles.statusText}>{statusText}</Text>

        <View style={styles.middleButtonsRow}>
          <Pressable
            onPress={() => router.push("/schedule")}
            style={({ pressed }) => [styles.midButton, pressed && styles.midButtonPressed]}
          >
            <Text style={styles.midButtonText}>Schedule</Text>
          </Pressable>

          <Pressable
            onPress={() => router.push("/history")}
            style={({ pressed }) => [styles.midButton, pressed && styles.midButtonPressed]}
          >
            <Text style={styles.midButtonText}>History</Text>
          </Pressable>
        </View>
      </View>

      <BottomNav />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: BG,
  },
  mainCard: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: BG,
  },
  restaurantLabel: {
    position: "absolute",
    top: 30,
    left: 32,
    fontWeight: "600",
    fontSize: 16,
  },
  bulbWrapper: {
    width: BULB_SIZE + 120,
    height: BULB_SIZE + 150,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 40,
  },
  bulbCircle: {
    width: BULB_SIZE,
    height: BULB_SIZE,
    borderRadius: BULB_SIZE / 2,
    marginBottom: 0,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 10,
    elevation: 6,
  },
  bulbNeck: {
    width: BULB_SIZE * 0.35,
    height: 50,
    borderRadius: 8,
    marginTop: -10,
    marginBottom: 6,
  },
  baseBar: {
    width: BULB_SIZE * 0.55,
    height: 16,
    borderRadius: 12,
    marginTop: 10,
    shadowColor: "#221f06ff",
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 7 },
    shadowRadius: 5,
    elevation: 3,
  },
  ray: {
    position: "absolute",
    width: 70,
    height: 12,
    borderRadius: 10,
    backgroundColor: "#FFF58A",
    shadowColor: "#FFF58A",
    shadowOpacity: 0.8,
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 12,
  },
  rayTop: {
    top: -40,
    left: "50%",
    marginLeft: -35,
    transform: [{ rotate: "90deg" }],
  },
  rayLeft: {
    top: 80,
    left: -25,
  },
  rayRight: {
    top: 80,
    right: -25,
  },
  rayTopLeft: {
    top: 0,
    left: 0,
    transform: [{ rotate: "35deg" }],
  },
  rayTopRight: {
    top: 0,
    right: 0,
    transform: [{ rotate: "-35deg" }],
  },
  rayMiddleBottomLeft: {
    left: -10,
    top: "50%",
    transform: [{ rotate: "-25deg" }],
    marginTop: -6,
  },
  rayMiddleBottomRight: {
    right: -10,
    top: "50%",
    transform: [{ rotate: "25deg" }],
    marginTop: -6,
  },
  rayBottomLeft: {
    bottom: 95,
    left: 25,
    transform: [{ rotate: "-45deg" }],
  },
  rayBottomRight: {
    bottom: 95,
    right: 25,
    transform: [{ rotate: "45deg" }],
  },
  statusText: {
    marginTop: 24,
    fontSize: 24,
    fontWeight: "800",
  },
  middleButtonsRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 40,
    columnGap: 20,
  },
  midButton: {
    width: 140,
    height: 48,
    backgroundColor: "#FFFFFF",
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#E2E8E1",
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 8,
    elevation: 3,
  },
  midButtonPressed: {
    backgroundColor: "#F1F4F0",
    borderColor: "#C9D5C6",
  },
  midButtonText: {
    fontWeight: "700",
    fontSize: 16,
    color: "#2E442A",
    letterSpacing: 0.3,
  },
});
