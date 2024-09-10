########################################################################
# Project name       :   Apollo Temp + Humidity IoT automation
# Description        :   [+] Reads temp and humidity at my local area 
#                    :   [+] and posts data/readings at Slack 
# @andrei           :   20230811 : initial codes created
# @bencarpena       :   20230630 :  Added HERMES protocol; send all messages (system and product) to HERMES
#                             :
#                             :  [Architecture + Workflow] 
#                             :      apollo (sender) --> alphard (rabbitmq queue) 
#                             :
########################################################################


import sys

import Adafruit_DHT

import ssl, os
import requests
import json

import subprocess

from gpiozero import LED
from time import sleep
#from datetime import datetime, timezone
from datetime import datetime
import math

import RPi.GPIO as GPIO

from paho.mqtt import client as mqtt
import pytz
import os

from multiprocessing import Process
from urllib import request

import utils.hermes

#from slack import WebClient 

# Main
webhook_url = 'https://hooks.slack.com/services/xxx/xxx/xxx' #apollo @ IntegrationHq2

# Demo for public
webhook_url_supercharged_hagrid = 'https://hooks.slack.com/services/xxx/xxx/xxx'

# Location
IOT_LOC = '30.112014921764576, -95.54612274151808'

raspi_current_ip  = subprocess.check_output("ifconfig -a | grep cast | grep net", shell=True, universal_newlines=True).strip()
output_ip = raspi_current_ip.split(' ')[1]

def has_internet():
    try:
        request.urlopen('http://google.com', timeout=1)
        return True
    except request.URLError as err: 
        return False

#os.system('cpu=$(</sys/class/thermal/thermal_zone0/temp) && echo "$((cpu/1000)) C" > /home/pi/Scripts/cputemp.log')
cpu_temperature_exec = subprocess.check_output('cat /sys/class/thermal/thermal_zone0/temp', shell=True, universal_newlines=True).strip()
cpu_temperature_exec = int(cpu_temperature_exec) / 1000
cpu_temperature = str(cpu_temperature_exec) + ' C'
gpu_temperature = subprocess.check_output("vcgencmd measure_temp | egrep  -o  '[[:digit:]].*'", shell=True, universal_newlines=True).strip().replace("'", " ")

if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)): 
			ssl._create_default_https_context = ssl._create_unverified_context

# Parse command line parameters.
sensor_args = { '11': Adafruit_DHT.DHT11,
                '22': Adafruit_DHT.DHT22,
                '2302': Adafruit_DHT.AM2302 }
if len(sys.argv) == 3 and sys.argv[1] in sensor_args:
    sensor = sensor_args[sys.argv[1]]
    pin = sys.argv[2]
else:
    #20230111 : upgraded
    #print('Usage: sudo ./Adafruit_DHT.py [11|22|2302] <GPIO pin number>')
    #print('Example: sudo ./Adafruit_DHT.py 2302 4 - Read from an AM2302 connected to GPIO pin #4')
    slack_msg = {'text' : 'Apollo the Blessed (weather_man | iot/w01) : System usage error : Read from an AM2302 connected to GPIO pin #4 | ip : ' + output_ip + ' '}
    requests.post(webhook_url, data=json.dumps(slack_msg))
    sys.exit(1)

# Try to grab a sensor reading.  Use the read_retry method which will retry up
# to 15 times to get a sensor reading (waiting 2 seconds between each retry).
humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

# Un-comment the line below to convert the temperature to Fahrenheit.
# temperature = temperature * 9/5.0 + 32

# Note that sometimes you won't get a reading and
# the results will be null (because Linux can't
# guarantee the timing of calls to read the sensor).
# If this happens try again!


led = LED(17)

def illuminate_led(seconds):
    #debugonly : print ("INFO: illuminating status led...")
    led.on()
    sleep(int(seconds))
     

def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n*multiplier + 0.5) / multiplier


def on_connect(client, userdata, flags, rc):
    print("apollo (mode: iot/w01) connected with result code: " + str(rc))


def on_disconnect(client, userdata, rc):
    print("apollo (mode: iot/w01) disconnected with result code: " + str(rc))


def on_publish(client, userdata, mid):
    print("apollo (mode: iot/w01) sent message!")
    print("JSON payload sent: ", slack_msg_mqtt)


def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)

def on_log(client, userdata, level, buf):
    print("log: ",buf)



def get_sensor_readings():
    #debugonly : print ("INFO: getting sensor readings...")
    blnExecute = True
    while blnExecute == True:

        #debug only client = slack.WebClient('xoxb-xxx-xxx-xxx')
        if humidity is not None and temperature is not None:
            #20190727 @bencarpena : Added feature to turn on/off LED            
            #20230112 : print('Temp={0:0.1f}*  Humidity={1:0.1f}%'.format(temperature, humidity))
            #20230112 : print(temperature) #20210227 debug only

            # ##########################################################
            # OUTPUT
            #   20230112 : upgraded output message 
            # ##########################################################
            
            print('dt local : ' + str(datetime.now()) + '| dt utc : ' + str(datetime.now(pytz.utc)) + ' | Location : ' + IOT_LOC + ' | Temperature : ' 
                  + str(round_half_up(temperature, 1)) + ' C | Humidity : ' 
                  + str(round_half_up(humidity, 1)) + ' %' )

            dtstamp = datetime.now()
            
            if round_half_up(temperature, 1) >= 29:
                slack_msg = {'text' : 'Apollo the Blessed (weather_man - iothub bypass dht) | ' + str(dtstamp) + ' | Temperature : ' + str(round_half_up(temperature, 1)) + ' C | Humidity : ' + str(round_half_up(humidity, 1)) + ' % :hot_face:', 'icon_emoji' : 'hot_face'}
                requests.post(webhook_url, data=json.dumps(slack_msg))
            elif 0 <= round_half_up(temperature, 1) <= 16:
                slack_msg = {'text' : 'Apollo the Blessed (weather_man - iothub bypass dht) | ' + str(dtstamp) + ' | Temperature : ' + str(round_half_up(temperature, 1)) + ' C | Humidity : ' + str(round_half_up(humidity, 1)) + ' %  :cold_face: ' , 'icon_emoji' : 'cold_face'}
                requests.post(webhook_url, data=json.dumps(slack_msg))
            else:
                slack_msg = {'text' : 'Apollo the Blessed (weather_man - iothub bypass dht) | ' + str(dtstamp) + ' | Temperature : ' + str(round_half_up(temperature, 1)) + ' C | Humidity : ' + str(round_half_up(humidity, 1)) + ' %  '}
                requests.post(webhook_url, data=json.dumps(slack_msg))
            
            slack_msg = {'text' : 'Apollo the Blessed (weather_man - iothub bypass dht) | ip : ' + output_ip + ' | Location : ' + IOT_LOC + ''}
            requests.post(webhook_url, data=json.dumps(slack_msg))

            slack_msg_supercharged_hagrid = {'text' : 'Apollo for South Houston High School | ' + str(dtstamp) + ' | Temperature : ' + str(round_half_up(temperature, 1)) + ' C | Humidity : ' + str(round_half_up(humidity, 1)) + ' % '}
            requests.post(webhook_url_supercharged_hagrid, data=json.dumps(slack_msg_supercharged_hagrid))

            # 20230630 : added
            _hostname = subprocess.check_output("hostname", shell=True, universal_newlines=True)
            utils.hermes.send_messages('hermes', 'server : ' + str(_hostname).replace('\n', '') + ' | dt local : ' + str(datetime.now()) + '| dt utc : ' + str(datetime.now(pytz.utc)) + ' | Location : ' + IOT_LOC + ' | Temperature : ' 
                  + str(round_half_up(temperature, 1)) + ' C | Humidity : ' 
                  + str(round_half_up(humidity, 1)) + ' %')
            
            #print("Hermes messsage sent") #debugonly
            '''
            #debug only
            #add emoji to Slack
            response = client.reactions_add(
            channel="#cvx-iot-apollo",
            name="smile",
            timestamp=str(dtstamp)
            )
            '''
        
            # 20230111 : print ("Success : Posted data to Slack!")

            #20201226 : Updated to send JSON payload
            #slack_msg_mqtt = 'apollo(iot/w01) | ' + str(dtstamp) + ' | Temperature : ' + str(round_half_up(temperature, 1)) + ' C | Humidity : ' + str(round_half_up(humidity, 1)) + ' %'
            slack_msg_mqtt = '{"iot_msg_from" : "Hagrid : apollo(iot/w01)", "iot_dt" : "' + str(dtstamp) + '", "iot_rd" : "sensor = am2302 | Temperature = ' + str(round_half_up(temperature, 1)) + ' C | Humidity = ' + str(round_half_up(humidity, 1)) + ' %"}'
            blnExecute = False

            # @bencarpena 20201219 : Send message to IoT Hub via MQTT
            # START : MQTT < #############################
            path_to_root_cert = "/home/pi/Scripts/certs/Baltimore.pem"
            device_id = "alphard02"
            sas_token = "SharedAccessSignature sr=iotpythonmqtt.azure-devices.net%2Fdevices%2Falphard02&sig=zsKbgk0I0oIn%2BCykU1a9ROKWwQOvdSQo7IZ%2B5udKVAo%3D&se=1634061314"
            iot_hub_name = "iotpythonmqtt"


            client = mqtt.Client(client_id=device_id, protocol=mqtt.MQTTv311)
            client.on_message=on_message 
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            client.on_publish = on_publish

            client.username_pw_set(username=iot_hub_name+".azure-devices.net/" +
                                device_id + "/?api-version=2018-06-30", password=sas_token)

            client.tls_set(ca_certs=path_to_root_cert, certfile=None, keyfile=None,
                        cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
            client.tls_insecure_set(False)

            client.connect(iot_hub_name+".azure-devices.net", port=8883)

            #start the loop
            client.loop_start() 

            #subscribe to topic
            client.subscribe("devices/" + device_id + "/messages/events/")

            #publish message
            client.publish("devices/" + device_id + "/messages/events/", slack_msg_mqtt, qos=1) 

            #give time to process subroutines
            sleep(5)

            #display log
            client.on_log=on_log


            #end the loop
            client.loop_stop()

            # END MQTT > #############################
        else:
            #print('Failed to get reading. Try again!')
            console_data = subprocess.check_output("uptime", shell=True, universal_newlines=True)
            slack_msg = {'text' : 'Apollo the Blessed (weather_man | iot/w01) : Error occurred! : failed to get reading. Try again or fix me please. | ip : ' + output_ip + ' | dt : ' + str(datetime.now())}
            requests.post(webhook_url, data=json.dumps(slack_msg))
            slack_msg = {'text' : 'Apollo the Blessed (weather_man | iot/w01) : System Uptime : ' + console_data}
            requests.post(webhook_url, data=json.dumps(slack_msg))

            # 20230630 : added
            utils.hermes.send_messages('hermes', 'server : apollo | dt local : ' + str(datetime.now()) + '| dt utc : ' + str(datetime.now(pytz.utc)) + ' | Location : ' + IOT_LOC + ' | Temperature : ' 
                  ' ERROR | Humidity : ERROR ')
            
            blnExecute = False


def get_sensor_readings_offlinemode():
    #debugonly : print ("INFO: getting sensor readings...")
    blnExecute = True
    while blnExecute == True:
        if humidity is not None and temperature is not None:
            print('dt local : ' + str(datetime.now()) + '| dt utc : ' + str(datetime.now(pytz.utc)) 
                  + ' | Location : ' + IOT_LOC + ' | Temperature : ' 
                  + str(round_half_up(temperature, 1)) + ' C | Humidity : ' 
                  + str(round_half_up(humidity, 1)) + ' %' )
            blnExecute = False
        else:
            print('dt local : ' + str(datetime.now()) + '| dt utc : ' + str(datetime.now(pytz.utc)) + 
                  ' | Location : ' + IOT_LOC + ' | Temperature : error ' 
                  + '| Humidity : error' )
            blnExecute = False

    
# ###################################
# CODE DRIVER
# ###################################

try:
    if has_internet() == True:
        Process(target=illuminate_led, args=(10,)).start()
        Process(target=get_sensor_readings).start()
    else:
        Process(target=illuminate_led, args=(10,)).start()
        Process(target=get_sensor_readings_offlinemode).start()
    
except:
    _exception = sys.exc_info()[0]
    raspi_current_ip  = subprocess.check_output("ifconfig -a | grep cast | grep net", shell=True, universal_newlines=True).strip()
    output_ip = raspi_current_ip.split(' ')[1]
    
    if "socket.gaierror" in str(_exception): 
        # 20210908 @bencarpena : Azure iot hub deactivated; no cause for alarm
        #slack_msg = {'text' : 'Apollo the Blessed (weather_man | iot/w01) : Exception occurred! ' + str(datetime.now())}
        slack_msg = {'text' : 'Apollo the Blessed (weather_man | iot/w01) : Hmmm... OK! ' + str(datetime.now())}
        requests.post(webhook_url, data=json.dumps(slack_msg))
        console_data = subprocess.check_output("uptime", shell=True, universal_newlines=True)
    else:
        slack_msg = {'text' : 'Apollo the Blessed (weather_man | iot/w01) : Error occurred! : Exception message = ' + str(_exception) + ' ' + str(datetime.now())}
        requests.post(webhook_url, data=json.dumps(slack_msg))

    #os.execv(__file__, sys.argv) 
finally:
    # Get free disk space and % free ====
    #mymac : df_data  = subprocess.check_output("df -kh | grep disk3s1s1", shell=True, universal_newlines=True).strip()
    if has_internet() == True:
        df_data  = subprocess.check_output("df -kh | grep root", shell=True, universal_newlines=True).strip()
        avail_disk_size = df_data.split('  ')[6].strip()
        percentage_disk_free = df_data.split('  ')[7].strip().replace('/' ,'')
        final_percentage_disk_free = 100 - int(percentage_disk_free.replace('%', ''))

        slack_msg = {'text' : 'Apollo the Blessed (weather_man | iot/w01) : Free Disk space : ' + avail_disk_size + ' | % free : ' + str(final_percentage_disk_free) + '% '}
        requests.post(webhook_url, data=json.dumps(slack_msg))

        console_data = subprocess.check_output("uptime", shell=True, universal_newlines=True)
        slack_msg = {'text' : 'Apollo the Blessed (weather_man | iot/w01) : System Uptime : ' + console_data + ' | ip : ' + output_ip + ' | cpu temp : ' + str(cpu_temperature) + ' | gpu temp : ' + str(gpu_temperature)}
        requests.post(webhook_url, data=json.dumps(slack_msg))

