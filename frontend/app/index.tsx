import { View, Text, TextInput, Pressable, StyleSheet, Image } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Link } from "expo-router";

export default function LoginScreen() {
  const logo = require("../assets/budderfly_logo.png");

  return (
    <View style={styles.container}>
      <Image source={logo} style={styles.logo} />

      <View style={styles.content}>
        <Text style={styles.title}>Welcome!</Text>

        <TextInput
          placeholder="Username"
          placeholderTextColor="#7A8275"
          style={styles.input}
        />
        <TextInput
          placeholder="Password"
          placeholderTextColor="#7A8275"
          secureTextEntry
          style={styles.input}
        />

        <Link href="/dashboard" asChild>
          <Pressable style={styles.buttonWrapper}>
            <LinearGradient
              colors={["#3B6D31", "#C9FF6A"]}
              start={{ x: 0, y: 0.5 }}
              end={{ x: 1, y: 0.5 }}
              style={styles.button}
            >
              <Text style={styles.buttonText}>Login</Text>
            </LinearGradient>
          </Pressable>
        </Link>
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
  buttonText: {
    color: "white",
    fontWeight: "800",
    fontSize: 20,
  },
});
