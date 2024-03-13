import asyncio
import websockets

class WSSBroadcastServer():

    def __init__(self, HOST='127.0.0.1', PORT=8765):
        self.host = HOST
        self.port = PORT

        # Set to store all connected clients
        self.clients = set()
        self.wbsclient = None


    async def handle_client(self, websocket, path):
        # Add the client to the set of connected clients
        self.clients.add(websocket)
        try:
            async for message in websocket:
                # Broadcast the received message to all connected clients except the sender
                for client in self.clients:
                    if client != websocket:  # Exclude the sender
                        await client.send(message)
        finally:
            # Remove the client from the set of connected clients when the connection is closed
            self.clients.remove(websocket)


    async def send_message(self, message):
        if(self.wbsclient == None):
            print("wbsclient not yet initiated")
        else:
            await self.wbsclient.send(message)


    async def start_server(self):
        server = await websockets.serve(self.handle_client, self.host, self.port)
        self.wbsclient = await websockets.connect("ws://" + self.host + ":" + str(self.port))
        await server.wait_closed()  # This will keep running until the server is closed.
        
        


""" 
USAGE: 
-----------
SERVER
-----------
from wssbroadcastserver import WSSBroadcastServer
import asyncio

async def main():
    wsserver = WSSBroadcastServer('127.0.0.1', 8765)
    asyncio.create_task(wsserver.start_server_async())  # This now runs in the background
    print("helloooo")
    while True:
        await asyncio.sleep(1)

# Ensuring the main coroutine is run
if __name__ == "__main__":
    asyncio.run(main())

-----------
CLIENT
-----------
import asyncio
from wssbroadcastserver import WSSBroadcastServer


wsserver = WSSBroadcastServer('127.0.0.1', 8765)

while True:
    message = input("Enter message to send: ")
    asyncio.run(wsserver.send_message(message))

-----------
"""
