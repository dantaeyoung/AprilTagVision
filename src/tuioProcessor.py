from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc import udp_client
import time
import asyncio
import json
import paho.mqtt.client as mqtt

from wssbroadcastserver import WSSBroadcastServer

import utils


# this is how many seconds of disappearance the processor should ignore. A higher value leads to more stable values, but more latency. A lower value leads to more sensitivity but more flickering. Generally 0.05 - 0.5 seems to be a good range, with about 0.2 as a sweet spot.

# AS A NOTE, the minimum value of this is gated by NEG_FSEQ_FREQ in `apriltagvision.py`. 

sensitivity_time = 0.2 


# Dictionary to store the last appearance frame for each tag ID
last_tags_appearance = {}


tags_homeassistant_config = {
    100: "number",
    101: "number",
    102: "number",
    6: "binary_sensor",
    78: "binary_sensor"
}


def broadcast_data(address, data):
    global wsserver
    global oscclient
    global mqttc

    message = json.dumps(data)

    print("[BROADCAST] " + address + " -- " + message)
    if wsserver:
        asyncio.create_task(wsserver.send_message(message))
    if oscclient:
        oscclient.send_message(address, message)
    if mqttc:
        #mqttc.publish("test", message)
        print(data)
        if data['tagid'] == 102 and "ang" in data:
            ang = round(utils.radians_to_number(data['ang']))
            print(ang)
            mqttc.publish("homeassistant/number/apriltagvision1/tag102/state", ang)
        if data['change'] == 'appeared':
            print(f"homeassistant/binary_sensor/apriltagvision1/tag{ data['tagid']}/state", "1")
            mqttc.publish(f"homeassistant/binary_sensor/apriltagvision1/tag{ data['tagid']}/state", "1")
        if data['change'] == 'disappeared':
            mqttc.publish(f"homeassistant/binary_sensor/apriltagvision1/tag{ data['tagid']}/state", "0")
        print(data)

def handle_2dobj(address, *args):
    global oscclient
    global last_tags_appearance

    current_time = time.time()

    command = args[0]
    if command == "set":
        tag_id = args[2]


        thistag = {
            'tagid': args[2],
            'change': '',
            'xpos': args[3],
            'ypos': args[4],
            'ang': args[5],
            'xvel': args[6],
            'yvel': args[7],
            'angvel': args[8]
        }


        # Announce if the tag has newly appeared
        if tag_id not in last_tags_appearance:
            thistag['change'] = 'appeared'
            broadcast_data(f"/tuio/{tag_id}", thistag)
            # TAG NEWLY APPEARED
            print(f"Tag {tag_id} newly appeared at ({thistag['xpos']}, {thistag['ypos']}), angle {thistag['ang']}")


        # Announce if tag has moved
        if(thistag['xvel'] > 0 or thistag['yvel'] > 0 or thistag['angvel'] > 0):
            thistag['change'] = 'moved'
            broadcast_data(f"/tuio/{tag_id}", thistag)


        # update list of when this tag appeared
        last_tags_appearance[tag_id] = current_time




    # this command comes at the end of a TUIO sequence
    if command == "fseq":
        for (tag_id, la) in last_tags_appearance.copy().items():

            # Announce if the tag has newly disappeared
            if(current_time - la >= sensitivity_time):
                thistag = {
                    'tagid': tag_id,
                    'change': 'disappeared',
                }
                broadcast_data(f"/tuio/{tag_id}", thistag)
                print(f"Tag {tag_id} disappeared")
                del last_tags_appearance[tag_id]


# Define a function to handle incoming OSC messages
def print_message(address, *args):
    print(f"Received message addressed to {address}: {args}")


async def init_websocketserver():
    global wsserver
    wsserver = WSSBroadcastServer('127.0.0.1', 8765)
    print("Creating a websocket server on port 8765...")
    await wsserver.start_server()  # This now properly waits for the server to run





    
async def loop():
    while True:
        await asyncio.sleep(0)


async def init_TUIO_listener():
    # Create a dispatcher
    dispatcher = Dispatcher()
    dispatcher.map("/tuio/2Dobj", handle_2dobj)  # Map OSC address to the handler function

    server = AsyncIOOSCUDPServer(('127.0.0.1', 3333), dispatcher, asyncio.get_event_loop())
    transport, protocol = await server.create_serve_endpoint()  # Create datagram endpoint and start serving
    print("Listening for OSC messages on port 3333...")


async def init_OSC_broadcast():
    global oscclient
    oscclient = udp_client.SimpleUDPClient("127.0.0.1", 3334)  # OSC client to send messages
    print("Ready to broadcasting processed OSC messages on port 3334...")






def send_mqtt_discover_payload(client):


    for tagid, tagtype in tags_homeassistant_config.items():

        payload = {
           "unique_id": f"atv1_t{tagid}",
           "name": f"ATV 1 Tag {tagid}",
           "state_topic": f"homeassistant/apriltagvision1/tag{tagid}/state",
           "device":{
              "identifiers":[
                 "apriltagvision1"
              ],
              "name":"AprilTagVision1"
           }
        }

        if tagtype == "binary_sensor":
            payload['payload_on'] = "1"
            payload['payload_off'] = "0"

        if tagtype == "number":
            payload['min'] = "0"
            payload['max'] = "100"
            payload["command_topic"]: f"homeassistant/number/apriltagvision1/tag{tagid}/set"
    
        client.publish(f"homeassistant/{tagtype}/apriltagvision1/tag{tagid}/config", json.dumps(payload))
        print("sending ", json.dumps(payload))



def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    send_mqtt_discover_payload(client)


async def init_mqtt_broadcast():
    global mqttc
    mqttbroker_address = "100.91.199.119"
    mqttbroker_port = 1883

    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_username = utils.get_key('mqtt_username')
    mqtt_password = utils.get_key('mqtt_password')
    mqttc.username_pw_set(mqtt_username, mqtt_password)
    mqttc.on_connect = on_connect
    mqttc.connect(mqttbroker_address, mqttbroker_port, 60)

    mqttc.loop_start()
    print("Ready to broadcast MQTT messages")



class TuioProcessor:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def init_singleton(self):
        await asyncio.gather(
            init_OSC_broadcast(),
            init_mqtt_broadcast(),
            init_TUIO_listener(),
            init_websocketserver(),
        )



async def main():
    tuio_processor = TuioProcessor()
    await tuio_processor.init_singleton()



if __name__ == "__main__":
    asyncio.run(main())




