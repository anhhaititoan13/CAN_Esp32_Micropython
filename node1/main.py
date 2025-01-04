from mcp2515.canio import Timer, Message
from mcp2515.config import can_bus
from machine import Pin, ADC, PWM
from hcsr04 import HCSR04
import mfrc522

sender = Timer(2)
rdr = mfrc522.MFRC522(14, 13, 12, 4, 15)
#cardID = "0x25a81e00"
#e8a0570d
sensor = HCSR04(trigger_pin=32, echo_pin=33, echo_timeout_us=10000)
ldr = ADC(Pin(34))
servo = PWM(Pin(25), freq=50)
led_message = Pin(27, Pin.OUT)
led_card = Pin(26, Pin.OUT)

def rotate_servo(angle):
    duty = int(40 + (angle / 180) * 115)
    servo.duty(duty)

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
    if  sender.expired:
        sender.rewind_to(1.0)
        led_message.on()
        cardValue = rdr.getCardValue()
        print(cardValue)
        distance = int(sensor.distance_cm())
        light_level = ldr.read()
        if cardValue == cardID:
            card_status = 1
            rotate_servo(90)
            led_card.on()
        else:
            card_status = 0
            rotate_servo(0)
            led_card.off()
        distance = min(max(distance, 0), 255)
        light_status = 1 if light_level < 2500 else 0
        if cardValue:
            encoded_bytes = hex_to_decimal_pairs(cardValue[2:])
            print(encoded_bytes)
            data_to_send = bytes(encoded_bytes[:8] + [int(card_status), int(distance), int(light_status)])
        else:    
            data_to_send = bytes([int(card_status), int(distance), int(light_status)])
        message = Message(id=0x01, data=data_to_send, extended=False)
        send_success = can_bus.send(message)
        print("Send success:", send_success, "| ID:", hex(message.id), "| Data:", list(message.data), "| Detected Card:", cardValue, "| Distance:", distance, "cm", "| Light Level Status:", light_level)
    with can_bus.listen(timeout=0.1) as listener:
        led_message.off()
        message_count = listener.in_waiting()
        if message_count > 0:
            for _ in range(message_count):
                msg = listener.receive()
                if isinstance(msg, Message):
                    print("Received message from ID:", hex(msg.id))
                    if msg.id == 0x00:
                        cardID_parts = [hex(msg.data[i])[2:] for i in range(4)]
                        for i in range(1, 4):
                            if cardID_parts[i] == '0': 
                                cardID_parts[i] = '00'
                        cardID = "0x" + ''.join(cardID_parts)
                        print(cardID)






