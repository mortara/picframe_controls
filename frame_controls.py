#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from gpiozero import Button

import os
import time
import adafruit_dht
import board
import paho.mqtt.client as mqtt
import pprint

from configparser import ConfigParser
import json
from threading import Thread

picframe_paused = "OFF"

# Fuer jeden Button einen Callback

def button_callback_1(channel):
	if picframe_paused == 'OFF':
		__button_pressed("homeassistant/switch/picframe_paused/set","ON");
	else:
		__button_pressed("homeassistant/switch/picframe_paused/set","OFF");

def shutdownpin_pressed(channel):
	print("UPS signal")

def button_callback_1_held(channel):
	print("Shutdown initiated")
	os.system("sudo shutdown -h now")

def button_callback_2(channel):
    __button_pressed("homeassistant/button/picframe_back/set","ON");

def button_callback_3(channel):
    __button_pressed("homeassistant/button/picframe_next/set","ON");

button1 = Button('BOARD29', hold_time=5)
button1.when_pressed = button_callback_1
button1.when_held = button_callback_1_held

button2 = Button('BOARD31')
button2.when_pressed = button_callback_2

button3 = Button('BOARD36')
button3.when_pressed = button_callback_3

shutdownpin = Button('BOARD11', pull_up=False, hold_time=2) 
shutdownpin.when_held = button_callback_1_held
shutdownpin.when_pressed = shutdownpin_pressed

path_current_directory = os.path.dirname(__file__)
path_config_file = os.path.join(path_current_directory, 'config.ini')

# Jetzt wird der DHT22 eingerichtet
config = ConfigParser(delimiters=('=', ))
config.read(path_config_file)

pin = config['sensor'].get('pin', 10)
device_id = config['mqtt'].get('device_id', 'picframe_controls')
decim_digits = config['sensor'].getint('decimal_digits', 2)
sleep_time = config['sensor'].getint('interval', 60)
available_topic = "homeassistant/switch/picframe/available"

sensor_topic_head = "homeassistant/sensor/" + device_id



# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
	print("Connected with result code {}".format(rc))
	__setup_sensor(client, "Humidity", "%", 'mdi:percent', available_topic, 'diagnostic')
	__setup_sensor(client, "Temperature", "°C", 'mdi:temperature-celsius', available_topic, 'diagnostic')

	client.subscribe("homeassistant/switch/picframe_paused/state", qos=0)

def on_message(client, userdata, msg):  # The callback for when a PUBLISH message is received from the server. 
	global picframe_paused
	message = msg.payload.decode("utf-8")
	print("Message received-> " + msg.topic + " :" + message)  # Print a received msg

	if msg.topic == "homeassistant/switch/picframe_paused/state":
		picframe_paused = message

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

def __button_pressed(topic, payload):
	client.publish(topic,payload);
	print(topic + '=' + payload +' published. Sleeping ... ')

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(config['mqtt'].get('hostname', 'homeassistant'),
               config['mqtt'].getint('port', 1883),
               config['mqtt'].getint('timeout', 60))
client.loop_start()

dhtDevice = adafruit_dht.DHT22(board.D25)

while True:
    temperature = dhtDevice.temperature
    humidity = dhtDevice.humidity
	
    if humidity is not None and temperature is not None:
        data = {
		'Temperature': round(temperature, decim_digits),
			'Humidity': round(humidity, decim_digits)
		}
        
    client.publish(sensor_topic_head + "/state", json.dumps(data))
    pprint.pprint(data)
    print('Published. Sleeping ... ')

    time.sleep(sleep_time)
