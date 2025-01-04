from machine import Pin
from time import sleep
from mcp2515.canio import Timer, Message
from mcp2515.config import can_bus
import dht

dht_sensor = dht.DHT11(Pin(14))
relay_output = Pin(27, Pin.OUT)
led_message = Pin(26, Pin.OUT)
sender = Timer(2)

while True:
    try:
        if sender.expired:
            sender.rewind_to(1.0)
            dht_sensor.measure()
            temperature = dht_sensor.temperature()
            humidity = dht_sensor.humidity()
            data_to_send = bytes([int(temperature), int(humidity)])
            message = Message(id=0x02, data=data_to_send, extended=False)
            send_success = can_bus.send(message)
            print("Send success:", send_success, "| ID:", hex(message.id), "| Temperature:", temperature, "C", "| Humidity:", humidity, "%")
            sleep(1)

        with can_bus.listen(timeout=0.1) as listener:
            led_message.on()
            message_count = listener.in_waiting()
            if message_count > 0:
                for _ in range(message_count):
                    msg = listener.receive()
                    if isinstance(msg, Message):
                        print("Received message from ID:", hex(msg.id))
                        if msg.id == 0x01:
                            ldr_sensor = msg.data[2]
                            relay_output.value(1 if ldr_sensor == 1 else 0)
            led_message.off()
    except OSError as e:
        print('Failed to read sensor.')

