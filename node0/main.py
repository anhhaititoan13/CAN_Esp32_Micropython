from machine import Pin, PWM, SoftI2C, Timer
import ssd1306
import time
from time import sleep
from mcp2515.canio import Message, RemoteTransmissionRequest, Timer
from mcp2515.config import can_bus
import urequests  # Thư viện HTTP request
import network  # Thư viện WiFi

# Khởi tạo Timer
sender = Timer(2)

last_sent = 0

# Khởi tạo I2C và OLED
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

# Khởi tạo Buzzer và LED
buzzer = PWM(Pin(33))
buzzer.freq(1000)
buzzer.duty(0)
led1 = Pin(25, Pin.OUT)
led2 = Pin(26, Pin.OUT)
led1.value(0)
led2.value(0)

oled.fill(0)
oled.text('CAN BUS', 0, 0)
oled.text('Connecting WiFi...', 0, 10)
oled.show()

def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        print("Waiting for WiFi connection...")
        sleep(1)
    print("WiFi connected:", wlan.ifconfig())
    oled.fill_rect(0, x_start=0, y_start=10, width=128, height=10) 
    oled.text('WiFi Connected', 0, 10)
    oled.show()

SSID = "Hong Be Oi"  
PASSWORD = "khongchodau" 
connect_wifi(SSID, PASSWORD)
     
def fetch_rfid_data():
    url = "http://canbus.onlinewebshop.net/get_data.php"
    try:
        response = urequests.get(url)
        if response.status_code == 200:
            rfid_data = response.json() 
            print("RFID Data:", rfid_data)
            return rfid_data
        else:
            print("Failed to fetch data, Status Code:", response.status_code)
            return []
    except Exception as e:
        print("Error fetching data:", e)
        return []
def send_data_to_server(temp, hum):
    url = "http://canbus.onlinewebshop.net/insert_data.php"
    try:
        full_url = f"{url}?temp={temp}&hum={hum}"
        response = urequests.get(full_url)
        if response.status_code == 200:
            print(f"Data sent successfully: Temperature={temp}, Humidity={hum}")
        else:
            print(f"Failed to send data. Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error sending data: {e}")
def timed_send(current_time):
    global last_sent
    if current_time - last_sent >= 60:
        send_data_to_server(temp, hum)
        last_sent = current_time
def send():
    rfid_array = fetch_rfid_data()
    if rfid_array and isinstance(rfid_array, list):
        for rfid_entry in rfid_array:
            id_card = rfid_entry.get("id_card", "")
            if id_card:
                encoded_bytes = hex_to_decimal_pairs(id_card)
                if encoded_bytes:
                    message = Message(id=0x00, data=bytes(encoded_bytes[:8]), extended=False) 
                    send_success = can_bus.send(message)
                    if send_success:
                        print(f"Sent id_card {id_card} as {encoded_bytes}")
                    else:
                        print(f"Failed to send id_card {id_card}")
    else:
        print("No valid RFID data to send.")
        
def hex_to_decimal_pairs(hex_string):
    if len(hex_string) != 8:
        raise ValueError("Input must be exactly 8 characters long.")
    decimal_values = []
    for i in range(0, len(hex_string), 2):
        hex_pair = hex_string[i:i+2] 
        decimal_value = int(hex_pair, 16)  
        decimal_values.append(decimal_value)
    return decimal_values

while True:
    if sender.expired:
        sender.rewind_to(1.0)
        send()  
    
    with can_bus.listen(timeout=0.1) as listener:
        message_count = listener.in_waiting()
        if message_count > 0:
            for _ in range(message_count):
                msg = listener.receive()
                if isinstance(msg, Message):
                    print("Received message from ID:", hex(msg.id))
                    if msg.id == 0x01:
                        led1.on()
                        oled.fill_rect(0, x_start=0, y_start=0, width=128, height=30) 
                        if len(msg.data) == 3:
                            card_status = msg.data[0]
                            distance = msg.data[1]
                            light_status = msg.data[2]
                        elif len(msg.data) == 7:
                            cardID_parts = [hex(msg.data[i])[2:] for i in range(4)]
                            for i in range(1, 4):
                                if cardID_parts[i] == '0': 
                                    cardID_parts[i] = '00'
                            cardID = ''.join(cardID_parts)
                            print(cardID)
                            card_status = msg.data[4]
                            distance = msg.data[5]
                            light_status = msg.data[6]
                            oled.fill_rect(0, x_start=0, y_start=30, width=128, height=10)
                            if card_status==0:
                                oled.text(f"New ID: {cardID}", 0, 30)
                                oled.show()
                        print(f"Card Status: {card_status}, Distance: {distance} cm, Light Status: {light_status}")
                        if distance > 10 or distance == 0:
                            buzzer.duty(0)
                        else:
                            duty = max(10, (10 - distance) * 10)
                            buzzer.duty(duty)
                            buzzer.freq(1000 + (10 - distance) * 100)
                        oled.text("Door: CLOSE" if card_status == 0 else "Door: OPEN", 0, 0)
                        oled.text(f"Distance: {distance} cm", 0, 10)
                        oled.text("Light: OFF" if light_status == 0 else "Light: ON", 0, 20)
                        oled.show()
                        led1.off()
                    elif msg.id == 0x02:
                        led2.on()
                        oled.fill_rect(0, x_start=0, y_start=40, width=128, height=30)
                        temp = msg.data[0]
                        hum = msg.data[1]
                        print(f"Temperature: {temp}C, Humidity: {hum}%")
                        oled.text(f'Temperature: {temp}C', 0, 40)
                        oled.text(f"Humidity: {hum}%", 0, 50)
                        oled.show()
                        led2.off()
                        current_time = time.time()  
                        timed_send(current_time)  
                elif isinstance(msg, RemoteTransmissionRequest):
                    print("RTR length:", msg.length)







