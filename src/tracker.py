import cv2
import apriltag
import numpy
import time
import logging
import collections

from quaternions import *


capture = cv2.VideoCapture(2)

# Setup detector
options = apriltag.DetectorOptions(families="tag36h11",
					nthreads=8,
					quad_decimate=1.0,
					quad_blur=1.0)

options.tag_size = 1
detector = apriltag.Detector(options)

# fx, fy, cx, cy = (439.728624791082, 414.9782292326142, 401.53713338042627, 211.2873582752417)
fx, fy, cx, cy = (1070.6915287567535, 1067.0306009135409, 323.3232144492538, 323.54374730910564)

camera_params = (fx, fy, cx, cy)

def detect_tag(image):

	# List of all of the tag positions
	all_tags = []

	# Convert image to grayscale
	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

	# Find basic information about tag (center location, tag family...)
	results = detector.detect(gray)

	logging.debug('%s AprilTags detected', len(results))

	# Loop over the AprilTag detection results
	for r in results:
		# Extract the bounding box (x, y)-coordinates for the AprilTag
		# and convert each of the (x, y)-coordinate pairs to integers
		(ptA, ptB, ptC, ptD) = r.corners
		ptB = (int(ptB[0]), int(ptB[1]))
		ptC = (int(ptC[0]), int(ptC[1]))
		ptD = (int(ptD[0]), int(ptD[1]))
		ptA = (int(ptA[0]), int(ptA[1]))

		# Find the center (x, y)-coordinates of the AprilTag
		(cX, cY) = (int(r.center[0]), int(r.center[1]))

		# draw the tag family on the image
		tag_family = r.tag_family.decode("utf-8")

		# Extract pose using camera parameters
		pose, e0, e1 = detector.detection_pose(r, camera_params)

		# Scale position vectors by tag size
		# TODO: Check that this is correct
		pose[0][3] *= options.tag_size
		pose[1][3] *= options.tag_size
		pose[2][3] *= options.tag_size

		# Extract pose (x, y, z)-coodinates into indevidual variables
		x = pose[0][3]
		y = pose[1][3]
		z = pose[2][3]

		# Convert transform matrix to quaternion (fancy angle)
		quaternion = matrixToQuat(pose)
		# Quaternions can be converted into pitch, yaw, roll using quatToAxisAngle()

		tag_info = {
			'pose' : (x, y, z),
			'quaternion' : quaternion,
			'center' : (cx, cy),
			'corners' : (ptA, ptB, ptC, ptD),
			'tag_family' : tag_family,
			'raw_pose' : pose
		}

		all_tags.append(tag_info)
		

	return all_tags


def _draw_pose(overlay, camera_params, tag_size, pose, z_sign=1):

    opoints = numpy.array([
        -1, -1, 0,
         1, -1, 0,
         1,  1, 0,
        -1,  1, 0,
        -1, -1, -2*z_sign,
         1, -1, -2*z_sign,
         1,  1, -2*z_sign,
        -1,  1, -2*z_sign,
    ]).reshape(-1, 1, 3) * 0.5*tag_size

    edges = numpy.array([
        0, 1,
        1, 2,
        2, 3,
        3, 0,
        0, 4,
        1, 5,
        2, 6,
        3, 7,
        4, 5,
        5, 6,
        6, 7,
        7, 4
    ]).reshape(-1, 2)
        
    fx, fy, cx, cy = camera_params

    K = numpy.array([fx, 0, cx, 0, fy, cy, 0, 0, 1]).reshape(3, 3)

    rvec, _ = cv2.Rodrigues(pose[:3,:3])
    tvec = pose[:3, 3]

    dcoeffs = numpy.zeros(5)

    ipoints, _ = cv2.projectPoints(opoints, rvec, tvec, K, dcoeffs)

    ipoints = numpy.round(ipoints).astype(int)
    
    ipoints = [tuple(pt) for pt in ipoints.reshape(-1, 2)]

    for i, j in edges:
        cv2.line(overlay, ipoints[i], ipoints[j], (0, 255, 0), 1, 16)

    

while True:

	ret, image = capture.read()

	detections = detect_tag(image)

	for detection in detections:
		# print(detections.raw_pose)
		_draw_pose(image, camera_params, 1.0, detection['raw_pose'])
	cv2.imshow("Image", image)


	# Q to stop the program
	if cv2.waitKey(1) & 0xFF == ord('q'):
		break

capture.release()
cv2.destroyAllWindows()
