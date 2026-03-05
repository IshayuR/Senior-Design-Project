import { useState } from "react";
import { View, Text, TextInput, Pressable, StyleSheet, Image } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";

export default function LoginScreen() {
  const logo = require("../assets/budderfly_logo.png");
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // const [loading, setLoading] = useState(false);
  // const baseUrl = (process.env.EXPO_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

  const onLogin = () => {
    // Skip real auth for testing – just go to dashboard
    router.replace("/dashboard");

    // --- Commented out: real login via backend ---
    // if (!email || !password) {
    //   Alert.alert("Missing info", "Please enter both email and password.");
    //   return;
    // }
    // setLoading(true);
    // try {
    //   const response = await fetch(`${baseUrl}/auth/login`, {
    //     method: "POST",
    //     headers: { "Content-Type": "application/json" },
    //     body: JSON.stringify({ email, password }),
    //   });
    //   if (!response.ok) {
    //     const body = await response.json().catch(() => null);
    //     const message =
    //       (body && typeof body.detail === "string" && body.detail) ||
    //       `Login failed (${response.status})`;
    //     Alert.alert("Login failed", message);
    //     return;
    //   }
    //   router.replace("/dashboard");
    // } catch (err) {
    //   const message = err instanceof Error ? err.message : "Unexpected network error";
    //   Alert.alert("Network error", message);
    // } finally {
    //   setLoading(false);
    // }
  };

  return (
    <View style={styles.container}>
      <Image source={logo} style={styles.logo} />

      <View style={styles.content}>
        <Text style={styles.title}>Welcome!</Text>

        <TextInput
          value={email}
          onChangeText={setEmail}
          placeholder="Email"
          placeholderTextColor="#7A8275"
          style={styles.input}
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
        />
        <TextInput
          value={password}
          onChangeText={setPassword}
          placeholder="Password"
          placeholderTextColor="#7A8275"
          secureTextEntry
          style={styles.input}
        />

        <Pressable style={styles.buttonWrapper} onPress={onLogin}>
          <LinearGradient
            colors={["#3B6D31", "#C9FF6A"]}
            start={{ x: 0, y: 0.5 }}
            end={{ x: 1, y: 0.5 }}
            style={styles.button}
          >
            <Text style={styles.buttonText}>Login</Text>
          </LinearGradient>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#DEEAD9",
    alignItems: "center",
    justifyContent: "flex-start",
  },

  logo: {
    position: "absolute",
    top: 60,
    left: -40,
    width: 350,
    height: 350,
    resizeMode: "contain",
    opacity: 0.25,
  },

  content: {
    marginTop: 220,
    width: "80%",
    alignItems: "center",
  },
  title: {
    fontSize: 40,
    fontWeight: "900",
    color: "#000",
    alignSelf: "flex-start",
    marginBottom: 20,
  },
  input: {
    width: "100%",
    backgroundColor: "#F8FFE9",
    borderRadius: 16,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 18,
    marginBottom: 16,
    color: "#333",
  },
  buttonWrapper: {
    width: "100%",
    marginTop: 12,
  },
  button: {
    width: "100%",
    paddingVertical: 14,
    borderRadius: 999,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonDisabled: {
    opacity: 0.8,
  },
  buttonText: {
    color: "white",
    fontWeight: "800",
    fontSize: 20,
  },
});
