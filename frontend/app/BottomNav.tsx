import { Link, usePathname } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

export default function BottomNav() {
  const pathname = usePathname();
  const isDashboard = pathname === "/dashboard";
  const isProfile = pathname === "/profile";

  return (
    <View style={styles.wrapper}>
      <View style={styles.navContainer}>
        <Link href="/dashboard" asChild>
          <Pressable style={styles.tab}>
            <View style={[styles.pill, isDashboard && styles.pillActive]}>
              <Text style={[styles.label, isDashboard && styles.labelActive]}>Dashboard</Text>
            </View>
          </Pressable>
        </Link>

        <Link href="/profile" asChild>
          <Pressable style={styles.tab}>
            <View style={[styles.pill, isProfile && styles.pillActive]}>
              <Text style={[styles.label, isProfile && styles.labelActive]}>Profile</Text>
            </View>
          </Pressable>
        </Link>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    paddingBottom: 16,
    paddingTop: 4,
    backgroundColor: "#DEEAD9",
  },
  navContainer: {
    flexDirection: "row",
    marginHorizontal: 24,
    padding: 6,
    borderRadius: 28,
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#D0D9CC",
  },
  tab: {
    flex: 1,
  },
  pill: {
    borderRadius: 22,
    paddingVertical: 8,
    alignItems: "center",
    justifyContent: "center",
  },
  pillActive: {
    backgroundColor: "#E7F2E0",
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: "#5E6B55",
  },
  labelActive: {
    color: "#263822",
  },
});
