#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import os
import time
import Adafruit_DHT
import paho.mqtt.client as mqtt
import pprint

from configparser import ConfigParser
import json
from threading import Thread

# Fuer jeden Button einen Callback

def button_callback_1(channel):
    __button_pressed('Button1');
	
def button_callback_2(channel):
    __button_pressed('Button2');
	
def button_callback_3(channel):
    __button_pressed('Button3');
	
	
# Hier werden die Buttons eingerichtet
GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BOARD) # Use physical pin numbering

GPIO.setup(29, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Set pin 29 to be an input pin and set initial value to be pulled low (off)
GPIO.add_event_detect(29,GPIO.FALLING,callback=button_callback_1) # Setup event on pin 29 rising edge

GPIO.setup(31, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Set pin 29 to be an input pin and set initial value to be pulled low (off)
GPIO.add_event_detect(31,GPIO.FALLING,callback=button_callback_2) # Setup event on pin 29 rising edge

GPIO.setup(32, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Set pin 29 to be an input pin and set initial value to be pulled low (off)
GPIO.add_event_detect(32,GPIO.FALLING,callback=button_callback_3) # Setup event on pin 29 rising edge

# Jetzt wird der DHT22 eingerichtet
config = ConfigParser(delimiters=('=', ))
config.read('config.ini')

sensor_type = config['sensor'].get('type', 'dht22').lower()

if sensor_type == 'dht22':
    sensor = Adafruit_DHT.DHT22
elif sensor_type == 'dht11':
    sensor = Adafruit_DHT.dht11
elif sensor_type == 'am2302':
    sensor = Adafruit_DHT.AM2302
else:
    raise Exception('Supported sensor types: DHT22, DHT11, AM2302')

pin = config['sensor'].get('pin', 10)
device_id = config['mqtt'].get('device_id', 'picframe_controls')
decim_digits = config['sensor'].getint('decimal_digits', 2)
sleep_time = config['sensor'].getint('interval', 60)
available_topic = "homeassistant/switch/picframe/available"

sensor_topic_head = "homeassistant/sensor/" + device_id
button1_state = "unpressed"
button2_state = "unpressed"
button3_state = "unpressed"

last_temp = 0
last_hum = 0

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code {}".format(rc))
    __setup_sensor(client, "Humidity", "%", 'mdi:percent', available_topic, 'diagnostic')
    __setup_sensor(client, "Temperature", "°C", 'mdi:temperature-celsius', available_topic, 'diagnostic')
	
    __setup_sensor(client, "Button1", "Pressed", 'mdi:Switch', available_topic, 'diagnostic')
    __setup_sensor(client, "Button2", "Pressed", 'mdi:Switch', available_topic, 'diagnostic')
    __setup_sensor(client, "Button3", "Pressed", 'mdi:Switch', available_topic, 'diagnostic')
	
def __setup_sensor(client, topic, unit, icon, available_topic, entity_category=None): 
    config_topic = sensor_topic_head + "_" + topic + "/config"
    name = device_id + "_" + topic
    dict = {"name": name,
            "icon": icon,
			"unit_of_measurement": unit, 
            "value_template": "{{ value_json." + topic + "}}",
            "avty_t": available_topic,
            "uniq_id": name,
            "dev":{"ids":[device_id]}}
			
    dict["state_topic"] = sensor_topic_head + "/state"
	
    if entity_category:
        dict["entity_category"] = entity_category
								 
    config_payload = json.dumps(dict)
    client.publish(config_topic, config_payload, qos=0, retain=True)
    client.subscribe(device_id + "/" + topic, qos=0)
	
def __button_pressed(topic):
    data = { topic: 'Pressed'}
    client.publish(sensor_topic_head + "/state", json.dumps(data))
    time.sleep(0.5)
	
    __send_state()
    print(topic + ' pressed. Published. Sleeping ... ')
	
def __send_state():
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

    if humidity is not None and temperature is not None:
        temp_val = round(temperature, decim_digits)
        hum_val = round(humidity, decim_digits)
        last_temp = temp_val
        last_hum = hum_val
    else:
        temp_val = last_temp
        hum_val = last_hum

    data = {'Temperature': temp_val,
            'Humidity': hum_val,
			'Button1': button1_state,
			'Button2': button2_state,
			'Button3': button3_state}
				
    client.publish(sensor_topic_head + "/state", json.dumps(data))
    pprint.pprint(data)
    print('Published. Sleeping ... ')
	
client = mqtt.Client()
client.on_connect = on_connect
client.connect(config['mqtt'].get('hostname', 'homeassistant'),
               config['mqtt'].getint('port', 1883),
               config['mqtt'].getint('timeout', 60))
client.loop_start()

while True:

    __send_state()

    time.sleep(sleep_time)


GPIO.cleanup() # Clean up