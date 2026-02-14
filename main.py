import paho.mqtt.client as mqtt
import ssl

# Connection parameters
AWS_IOT_ENDPOINT = "aws:iot:620194173995:thing/esp32.iot.us-east-1.amazonaws.com"
PORT = 8883
CLIENT_ID = "esp32"

# Certificate files
CA_CERT = "AmazonRootCA1.pem"
CERTFILE = "1240a0688edce05d92364e9b50306a1d45857b8500bd2b7708e1fd36cbdb7182-certificate.pem.crt"
KEYFILE = "1240a0688edce05d92364e9b50306a1d45857b8500bd2b7708e1fd36cbdb7182-private.pem.key"

# Create MQTT client
client = mqtt.Client(client_id=CLIENT_ID)

# Set TLS authentication
client.tls_set(ca_certs=CA_CERT,
               certfile=CERTFILE,
               keyfile=KEYFILE,
               tls_version=ssl.PROTOCOL_TLSv1_2)

# Connect to AWS IoT Core
client.connect(AWS_IOT_ENDPOINT, PORT)

# Publish sample message to your topic
client.publish("restaurants/proof-of-concept/control", '{"state":"off"}')

client.disconnect()
