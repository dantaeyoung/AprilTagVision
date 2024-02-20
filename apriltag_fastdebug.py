import cv2
from pupil_apriltags import Detector
from pythonosc.udp_client import SimpleUDPClient
import threading
import argparse
import time

import utils

# Initialize the OSC client
ip = "127.0.0.1"
port = 3333  
osc_client = SimpleUDPClient(ip, port)


def send_tuio_messages(messages):
    for m in messages:
        osc_client.send_message(m[0], m[1])

def main():
    args = utils.parse_arguments()
    camera_index = args.camera
    frame_width = args.width
    frame_height = args.height
    verbose = args.verbose

    cap = cv2.VideoCapture(camera_index)  # Use the webcam
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    at_detector = Detector(families='tag36h11',
                           nthreads=1,
                           quad_decimate=1.0,
                           quad_sigma=0.0,
                           refine_edges=1,
                           decode_sharpening=0.25,
                           debug=0)

    # Track visible tags and their last known positions
    past_tags = {}

    tuio_fseq = 0
    last_negfseq_time = 0

    while True:
        # get frame from camera
        ret, frame = cap.read()
        if not ret:
            break


        # make frame grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # detect apriltags
        tags = at_detector.detect(gray, estimate_tag_pose=False, camera_params=None, tag_size=None)


        for tag in tags:
            print(tag)
            cv2.polylines(frame, [tag.corners.astype(int)], isClosed=True, color=(0, 255, 0), thickness=2)
            cv2.putText(frame, str(tag.tag_id), (int(tag.center[0]), int(tag.center[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
            
        # Display the frame
        cv2.imshow('AprilTag FastDebug', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

