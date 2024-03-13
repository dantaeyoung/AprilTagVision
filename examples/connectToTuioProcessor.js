
const connectToTuioProcessor = function(tuioEventHandler) {
    let socket = new WebSocket("ws://localhost:8765");

    socket.onopen = function(e) {
      console.log("[open] Connection established");
    };

    socket.onmessage = function(event) {
      tuioEventHandler(JSON.parse(event['data']))
    };

    socket.onclose = function(event) {
      if (event.wasClean) {
        console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
      } else {
        console.log('[close] Connection died');
      }
      setTimeout(connectToTuioProcessor, 2000); // Retry after 2 seconds
        
    };

    socket.onerror = function(error) {
      console.log(`[error]`);
    };
}


// Expose the connectToTuioProcessor function on the window object
window.connectToTuioProcessor = connectToTuioProcessor

