import React from "react";
import { View, Text, TextInput, Pressable, StyleSheet, Image, TouchableOpacity } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";

export default function LoginScreen() {
  const router = useRouter();
  const logo = require("../assets/budderfly_logo.png");
  const baseUrl = (process.env.EXPO_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  const handleLogin = async () => {
    setError(null);
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setError("Please enter both email and password.");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${baseUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: trimmedEmail,
          password,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          setError("Invalid email or password.");
        } else {
          let msg = `Login failed (${response.status}).`;
          try {
            const body = (await response.json()) as { detail?: unknown };
            const d = body.detail;
            if (typeof d === "string") {
              msg = d;
            }
          } catch {
            /* keep generic msg */
          }
          setError(msg);
        }
        return;
      }

      router.replace("/dashboard");
    } catch {
      setError("Could not connect to server. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Image source={logo} style={styles.logo} />

      <View style={styles.content}>
        <Text style={styles.title}>Welcome!</Text>

        <TextInput
          placeholder="Email"
          placeholderTextColor="#7A8275"
          style={styles.input}
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        <TextInput
          placeholder="Password"
          placeholderTextColor="#7A8275"
          secureTextEntry
          style={styles.input}
          value={password}
          onChangeText={setPassword}
        />

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <TouchableOpacity
          style={styles.buttonWrapper}
          activeOpacity={0.85}
          onPress={handleLogin}
          disabled={loading}
          accessibilityRole="button"
        >
          <LinearGradient
            colors={["#3B6D31", "#C9FF6A"]}
            start={{ x: 0, y: 0.5 }}
            end={{ x: 1, y: 0.5 }}
            style={[styles.button, loading && styles.buttonDisabled]}
            pointerEvents="none"
          >
            <Text style={styles.buttonText}>{loading ? "Logging in..." : "Login"}</Text>
          </LinearGradient>
        </TouchableOpacity>
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
    opacity: 0.7,
  },
  buttonText: {
    color: "white",
    fontWeight: "800",
    fontSize: 20,
  },
  errorText: {
    width: "100%",
    color: "#A0291E",
    fontSize: 14,
    marginTop: 4,
    marginBottom: 8,
  },
});
