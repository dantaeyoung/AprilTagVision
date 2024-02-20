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




        # send data via OSC using the TUIO protocol

        # the reason why I'm incrementing 100 is because these are temporary session ids, not fiducial marker ids. It's helpful to increment at an arbitrary number so that the arbitrary-ness isclear
        arbitrary_sessionid_start = 100

        # we gather all the messages before sending at once
        tuio_messages = []

        tuio_messages.append(["/tuio/2Dobj", ["source", "apriltagvision"]])
        tuio_messages.append(["/tuio/2Dobj", ["alive"] + list(range(arbitrary_sessionid_start, arbitrary_sessionid_start+len(tags)))])

    
        current_tags = {}

        ## the same arbitrary number
        session_id = arbitrary_sessionid_start 
        for tag in tags:
            session_id += 1

            current_tag = {}

            # x and y position
            current_tag['x'] = utils.round_and_threshold(tag.center[0] / frame_width, 0.0005, 7)
            current_tag['y'] = utils.round_and_threshold(tag.center[1] / frame_height, 0.0005, 7)

            # angle in radians
            current_tag['a'] = utils.round_and_threshold(utils.extract_rotation(tag.homography), 0.05, 4)

            # x and y and angle velocity (calculated as the delta from last tag)
            current_tag['X'] = 0
            current_tag['Y'] = 0
            current_tag['A'] = 0
            if tag.tag_id in past_tags:
                ptag = past_tags[tag.tag_id]
                tuio_X = utils.round_and_threshold((tag.center[0] / frame_width) - ptag['x'], 0.0005, 7)
                tuio_Y = utils.round_and_threshold((tag.center[1] / frame_height) - ptag['y'], 0.0005, 7)
                current_tag['X'] = tuio_X
                current_tag['Y'] = tuio_Y
                current_tag['A'] = utils.round_and_threshold(utils.angular_difference(ptag['a'], current_tag['a']), 0.05, 4)

            # motion and rotation acceleration.. not calculated for now
            current_tag['m'] = 0
            current_tag['r'] = 0

            tuio_messages.append(["/tuio/2Dobj", ["set", session_id, tag.tag_id, current_tag['x'], current_tag['y'], current_tag['a'], current_tag['X'], current_tag['Y'], current_tag['A'], current_tag['m'], current_tag['r']]])

            current_tags[tag.tag_id] = current_tag

            if(verbose):
                print(tag)

   

        # the last thing we send is a 'fseq' with the fseq id.
        # however, if the last two frames were exactly the same, send '-1'.
        # technically we should compare the last two frames. but in practice, this only happens when the last frame, as well as this frame, was completely free of tags.

        if(len(past_tags) == 0 and len(current_tags) == 0):
            # we also check the time to mimic reactivision behavior, which is to only send consecutive '-1' fseq messages once a second after the first one
            current_time = time.time()
            if(current_time - last_negfseq_time > 1):
                tuio_messages.append(["/tuio/2Dobj", ["fseq", -1]])
                send_tuio_messages(tuio_messages)
                if(verbose):
                    print(tuio_messages)
                last_negfseq_time = current_time
        else:
            tuio_messages.append(["/tuio/2Dobj", ["fseq", tuio_fseq]])
            send_tuio_messages(tuio_messages)
            if(verbose):
                print(tuio_messages)
            last_negfseq_time = 0

        # store our current tags as the past tags, so the next time around, we can calculate
        past_tags = current_tags

        # increment fseq
        tuio_fseq += 1

        # Create a copy of the grayscale frame to draw colored polylines
        displayframe = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        # Visualize detected tags
        for tag in tags:
            cv2.polylines(displayframe, [tag.corners.astype(int)], isClosed=True, color=(0, 255, 0), thickness=2)
            rotated_text_img, _, _ = utils.putRotatedText(displayframe, str(tag.tag_id), (int(tag.center[0]), int(tag.center[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2, current_tags[tag.tag_id]['a'])
            displayframe = cv2.add(displayframe, rotated_text_img)
            
#            cv2.putText(frame, str(tag.tag_id), (int(tag.center[0]), int(tag.center[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

        # Display the frame
        cv2.imshow('AprilTagVision (press q to quit)', displayframe)


        # if we get 'q' then exit this program
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

"""
  /tuio/2Dcur source application@address
  /tuio/2Dcur alive s_id0 ... s_idN
  /tuio/2Dcur set s_id x_pos y_pos x_vel y_vel m_accel
  /tuio/2Dcur fseq f_id

[Received OSC]:  {"address":"/tuio/2Dobj","args":["source","reacTIVision"]}
[Received OSC]:  {"address":"/tuio/2Dobj","args":["alive",7,8]}
[Received OSC]:  {"address":"/tuio/2Dobj","args":["set",7,1,0.5083478689193726,0.41566142439842224,4.032631874084473,0,0,0,0,0]}
[Received OSC]:  {"address":"/tuio/2Dobj","args":["set",8,0,0.31934550404548645,0.7052593231201172,5.802523612976074,0,0,0,0,0]}
[Received OSC]:  {"address":"/tuio/2Dobj","args":["fseq",5764]}
"""
