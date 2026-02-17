import { Stack } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

import { LightingProvider } from "../lightingStore";

export default function Layout() {
  return (
    <LightingProvider>
      <SafeAreaView style={{ flex: 1, backgroundColor: "#DEEAD9" }}>
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: "#DEEAD9" },
          }}
        />
      </SafeAreaView>
    </LightingProvider>
  );
}
