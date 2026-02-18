import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";

import BottomNav from "./BottomNav";

const BG = "#DEEAD9";

export default function ProfileScreen() {
  const router = useRouter();
  const [notificationsOn, setNotificationsOn] = React.useState(true);

  return (
    <View style={styles.screen}>
      <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent}>
        <Text style={styles.title}>Profile</Text>
        <Text style={styles.subtitle}>View your account details and restaurant settings.</Text>

        <View style={styles.topCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarInitials}>WW</Text>
          </View>
          <Text style={styles.name}>Wei Wei</Text>
          <Text style={styles.role}>Compsci Restaurant Owner</Text>
        </View>

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Restaurant</Text>
          <View style={styles.row}>
            <Text style={styles.label}>Name</Text>
            <Text style={styles.value}>Dairy Bar</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Location</Text>
            <Text style={styles.value}>Storrs, CT</Text>
          </View>
        </View>

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Account</Text>
          <View style={styles.row}>
            <Text style={styles.label}>Email</Text>
            <Text style={styles.value}>wei.wei@uconn.edu</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Notifications</Text>
            <Pressable
              onPress={() => setNotificationsOn(!notificationsOn)}
              style={[styles.toggleTrack, notificationsOn && styles.toggleTrackOn]}
            >
              <View style={[styles.toggleThumb, notificationsOn && styles.toggleThumbOn]} />
            </Pressable>
          </View>
        </View>

        <Pressable onPress={() => router.replace("/")} style={styles.linkButton}>
          <Text style={styles.linkButtonText}>Log out</Text>
        </Pressable>
      </ScrollView>

      <BottomNav />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: BG },
  container: { flex: 1 },
  scrollContent: { paddingHorizontal: 20, paddingTop: 24, paddingBottom: 16 },
  title: { fontSize: 24, fontWeight: "800", color: "#1F261E", marginBottom: 4 },
  subtitle: { fontSize: 14, color: "#5F6E5A", marginBottom: 18 },
  topCard: {
    backgroundColor: "#F2F7EF",
    borderRadius: 22,
    paddingVertical: 20,
    paddingHorizontal: 18,
    alignItems: "center",
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#DEE7D7",
  },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "#9BC87F",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  avatarInitials: { color: "white", fontSize: 28, fontWeight: "800" },
  name: { fontSize: 20, fontWeight: "800", color: "#1F261E" },
  role: { fontSize: 14, color: "#566555", marginTop: 2 },
  sectionCard: {
    backgroundColor: "#F2F7EF",
    borderRadius: 18,
    paddingVertical: 14,
    paddingHorizontal: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "#DEE7D7",
  },
  sectionTitle: { fontSize: 15, fontWeight: "700", color: "#263322", marginBottom: 8 },
  row: { flexDirection: "row", justifyContent: "space-between", marginTop: 6, alignItems: "center" },
  label: { fontSize: 13, color: "#5F6E5A" },
  value: { fontSize: 13, color: "#222A20", maxWidth: "60%", textAlign: "right" },
  toggleTrack: {
    width: 46,
    height: 26,
    borderRadius: 13,
    backgroundColor: "#D1D8CF",
    padding: 3,
    justifyContent: "center",
  },
  toggleTrackOn: { backgroundColor: "#9BC87F" },
  toggleThumb: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: "#FFFFFF",
    alignSelf: "flex-start",
  },
  toggleThumbOn: { alignSelf: "flex-end" },
  linkButton: { marginTop: 10, alignItems: "center" },
  linkButtonText: {
    fontSize: 14,
    color: "#7C4234",
    fontWeight: "600",
    textDecorationLine: "underline",
  },
});
