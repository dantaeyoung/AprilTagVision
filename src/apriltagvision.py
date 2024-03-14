import cv2
from pupil_apriltags import Detector
from pythonosc.udp_client import SimpleUDPClient
import threading
import argparse
import time

import utils


NEG_FSEQ_FREQ = 0.25
# this is the frequency at which negative fseq messages are sent. In practice, making this number smaller will allow downstream programs to be more reactive to tag disappearance.

# Initialize the OSC client
ip = "127.0.0.1"
port = 3333  
osc_client = SimpleUDPClient(ip, port)

# Variable to track pause state
paused = False

# Track visible tags and their last known positions
past_tags = {}



def handle_key_press(key):
    global paused
    if key == ord('q'):
        return False  # Indicate to quit
    elif key == ord('p'):
        paused = not paused
    return True

def generate_tuio_messages(rawtags, frame_width, frame_height):
    global verbose
    # send data via OSC using the TUIO protocol

    # the reason why I'm incrementing 100 is because these are temporary session ids, not fiducial marker ids. It's helpful to increment at an arbitrary number so that the arbitrary-ness isclear
    arbitrary_sessionid_start = 100

    # we gather all the messages before sending at once
    tuio_messages = []

    tuio_messages.append(["/tuio/2Dobj", ["source", "apriltagvision"]])
    tuio_messages.append(["/tuio/2Dobj", ["alive"] + list(range(arbitrary_sessionid_start, arbitrary_sessionid_start+len(rawtags)))])


    current_tags = {}

    ## the same arbitrary number
    session_id = arbitrary_sessionid_start 
    for tag in rawtags:
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

    return tuio_messages, current_tags




def create_displayframe(gray, rawtags, current_tags):
    # Create a copy of the grayscale frame to draw colored polylines
    displayframe = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    # Visualize detected tags
    for tag in rawtags:
        cv2.polylines(displayframe, [tag.corners.astype(int)], isClosed=True, color=(0, 255, 0), thickness=2)

        rotated_text_img, _, _ = utils.putRotatedText(displayframe, str(tag.tag_id), (int(tag.center[0]), int(tag.center[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2, current_tags[tag.tag_id]['a'])
        displayframe = cv2.add(displayframe, rotated_text_img)
    return displayframe



def send_messages(tuio_messages, past_tags, current_tags):
    global last_negfseq_time
    global tuio_fseq
    global verbose
   
    # the last thing we send is a 'fseq' with the fseq id.
    # however, if the last two frames were exactly the same, send '-1'.
    # technically we should compare the last two frames. but in practice, this only happens when the last frame, as well as this frame, was completely free of tags.



    if(len(past_tags) == 0 and len(current_tags) == 0):
        # we also check the time to mimic reactivision behavior, which is to only send consecutive '-1' fseq messages once a second after the first one
        current_time = time.time()
        if(current_time - last_negfseq_time > NEG_FSEQ_FREQ):
            tuio_messages.append(["/tuio/2Dobj", ["fseq", -1]])
            for m in tuio_messages:
                osc_client.send_message(m[0], m[1])
            if(verbose):
                print(tuio_messages)
            last_negfseq_time = current_time
    else:
        tuio_messages.append(["/tuio/2Dobj", ["fseq", tuio_fseq]])
        for m in tuio_messages:
            osc_client.send_message(m[0], m[1])
        if(verbose):
            print(tuio_messages)
        last_negfseq_time = 0

    # increment fseq
    tuio_fseq += 1


def run_apriltagvision():
    global paused
    global past_tags
    global last_negfseq_time
    global tuio_fseq
    global verbose

    args = utils.parse_arguments()
    camera_index = args.camera
    frame_width = args.width
    frame_height = args.height
    verbose = args.verbose
    headless = args.headless

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

    tuio_fseq = 0
    last_negfseq_time = 0

    while True:
        # get frame from camera
        ret, frame = cap.read()
        if not ret:
            break

        if not headless:
            # Pause processing if the program is paused
            if paused:
                cv2.putText(frame, "PAUSED", (20, frame_height // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 2)
                cv2.imshow('AprilTagVision (press p to pause, q to quit)', frame)
                key = cv2.waitKey(1) & 0xFF
                if not handle_key_press(key):
                    break
                continue


        # make frame grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # detect apriltags
        rawtags = at_detector.detect(gray, estimate_tag_pose=False, camera_params=None, tag_size=None)

        tuio_messages, current_tags = generate_tuio_messages(rawtags, frame_width, frame_height)


        send_messages(tuio_messages, past_tags, current_tags)


        # store our current tags as the past tags, so the next time around, we can calculate
        past_tags = current_tags

               

        if not headless:
            # Display the frame
            displayframe = create_displayframe(gray, rawtags, current_tags)
            cv2.imshow('AprilTagVision (press p to pause, q to quit)', displayframe)


            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if not handle_key_press(key):
                break


    cap.release()
    cv2.destroyAllWindows()

@profile
def main():
    run_apriltagvision()


if __name__ == "__main__":
    main()

