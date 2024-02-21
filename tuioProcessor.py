from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc import udp_client
import time
import asyncio
import websocket_utils
import json


# this is how many seconds of disappearance the processor should ignore. A higher value leads to more stable values, but more latency. A lower value leads to more sensitivity but more flickering. Generally 0.05 - 0.5 seems to be a good range, with about 0.2 as a sweet spot.

# AS A NOTE, the minimum value of this is gated by NEG_FSEQ_FREQ in `apriltagvision.py`. 

sensitivity_time = 0.2 


# Dictionary to store the last appearance frame for each tag ID
last_tags_appearance = {}


def broadcast_message(address, message):
    global wsserver
    global oscclient
    print("[BROADCAST] " + address + " -- " + message)
    if wsserver:
        asyncio.create_task(wsserver.send_message(message))
    if oscclient:
        oscclient.send_message(address, message)

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
            broadcast_message(f"/tuio/{tag_id}", json.dumps(thistag))
            # TAG NEWLY APPEARED
            print(f"Tag {tag_id} newly appeared at ({thistag['xpos']}, {thistag['ypos']}), angle {thistag['ang']}")


        # Announce if tag has moved
        if(thistag['xvel'] > 0 or thistag['yvel'] > 0 or thistag['angvel'] > 0):
            thistag['change'] = 'moved'
            broadcast_message(f"/tuio/{tag_id}", json.dumps(thistag))


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
                broadcast_message(f"/tuio/{tag_id}", json.dumps(thistag))
                print(f"Tag {tag_id} disappeared")
                del last_tags_appearance[tag_id]


# Define a function to handle incoming OSC messages
def print_message(address, *args):
    print(f"Received message addressed to {address}: {args}")


async def init_websocketserver():
    global wsserver
    wsserver = websocket_utils.WSSBroadcastServer('127.0.0.1', 8765)
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




async def main():
    await asyncio.gather(
        init_OSC_broadcast(),
        init_TUIO_listener(),
        init_websocketserver(),
    )

if __name__ == "__main__":
    asyncio.run(main())




