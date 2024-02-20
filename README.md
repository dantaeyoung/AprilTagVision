# AprilTagVision

![apriltagvision.png](apriltagvision.png)

AprilTagVision is a drop-in replacement for [reacTIVision](https://reactivision.sourceforge.net/), using the [Apriltags3](https://github.com/AprilRobotics/apriltags) library developed by [AprilRobotics](https://april.eecs.umich.edu/). The AprilTag library and its fiducial markers, are faster, smaller, and more robust. AprilTagVision uses [pupil-apriltags](https://github.com/pupil-labs/apriltags).



## Install

1. Download this repo to a local directory.

2. Recommended: Create a new virtual environment.

- Run the following command to create a new virtual environment. Replace 'venv' with the preferred name for your virtual environment: `python -m venv venv`
- Activate the virtual environment.
  - On Windows, you can do this with the following command: `venv\Scripts\activate`
  - On macOS and Linux, use the following command: `source venv/bin/activate`
- Once your virtual environment is activated, you should see the name of the virtual environment in the terminal.
- To deactivate the virtual environment, run the `deactivate` command in the terminal.

3. Install the dependencies listed in the requirements.txt file:
   `pip install -r requirements.txt`

## Running AprilTagVision

Like reacTIVision, AprilTagVision follows the [TUIO Protocol 1.1](https://www.tuio.org/?specification) and sends messages out via OSC on port 3333.

Basic:

- `python apriltag_tuio.py`
  
Select camera:

- `python apriltag_tuio.py --camera 2`

Select camera and force camera dimensions:

- `python apriltag_tuio.py --camera 3 --width 640 --height 480`

Select camera and output verbose debug output:

- `python apriltag_tuio.py --camera 1 --verbose`



## Troubleshooting

This code is currently only tested on a Mac M1. Please let me know if you try it on another OS or system!

Happy Hacking!
