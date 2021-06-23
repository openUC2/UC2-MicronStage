#!/usr/bin/env python
# coding: utf-8

import numpy as np
import matplotlib.pyplot as plt
import cv2
import serial
import time
from IPython.display import clear_output
import matplotlib
from IPython.display import display 
import ipywidgets as widgets 
from ipywidgets import interact, Layout 

import buffcam as buffcam
from scipy.ndimage import gaussian_filter

from scipy.ndimage.measurements import center_of_mass

import serial.tools.list_ports as port_list
import RPi.GPIO as GPIO
import sys
from typing import Optional
from vimba import *
from vimba.frame import FrameStatus

import tifffile as tif
import os
import grblboard as grbl

global iiter 

# laser shutter
# Pin Definitions
output_pin = 18  # BCM pin 18, BOARD pin 12
output_gnd = 17

# Pin Setup:
GPIO.setmode(GPIO.BCM)  # BCM pin-numbering scheme from Raspberry Pi
# set pin as an output pin with optional initial state of HIGH
GPIO.setup(output_pin, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(output_gnd, GPIO.OUT, initial=GPIO.HIGH)



# Setup Camera
timestr = time.strftime("%Y%m%d-%H%M%S")

# Prepare Camera for ActionCommand - Trigger
myexposure = 1000/1000 # in ms 
BLACKLEVEL = 100
mygain = 0
mybasepath = "./"
myfolder = timestr + "_PTYCHO_UC2-Texp-" + str(myexposure) + "_gain-" + str(mygain)
myfolder_TRACK = myfolder+"/TRACK"
iiter = 0
is_calib = True
is_display=False

offset_x = -0
offset_y = -0


# helper functions
def abort(reason: str, return_code: int = 1, usage: bool = False):
    print(reason + '\n')

    if usage:
        print_usage()

    sys.exit(return_code)

def get_camera(camera_id: Optional[str]) -> Camera:
    with Vimba.get_instance() as vimba:
        if camera_id:
            try:
                return vimba.get_camera_by_id(camera_id)

            except VimbaCameraError:
                abort('Failed to access Camera \'{}\'. Abort.'.format(camera_id))

        else:
            cams = vimba.get_all_cameras()
            if not cams:
                abort('No Cameras accessible. Abort.')

            return cams[0]

def setup_camera(cam: Camera):
    with cam:
        # Try to adjust GeV packet size. This Feature is only available for GigE - Cameras.
        try:
            cam.GVSPAdjustPacketSize.run()

            while not cam.GVSPAdjustPacketSize.is_done():
                pass

        except (AttributeError, VimbaFeatureError):
            pass
                
        #cam.TriggerSelector.set('FrameStart')
        #cam.TriggerActivation.set('RisingEdge')
        #cam.TriggerSource.set('Line0')
        #cam.TriggerMode.set('On')
        cam.BlackLevel.set(BLACKLEVEL)
        cam.ExposureAuto.set("Off")
        cam.ContrastEnable.set("Off")

        cam.ExposureTime.set(myexposure*1e3)
        #cam.PixelFormat.set('Mono12')
        cam.GainAuto.set("Off")
        cam.Gain.set(mygain)
        cam.AcquisitionFrameRateEnable.set(False)
        
        try:
             cam.get_feature_by_name("PixelFormat").set("Mono12")
        except:
             print("Mono8!!!!!!!!!!!!!!!!!!!!!!!")

try:
    os.mkdir(mybasepath+myfolder)
    os.mkdir(myfolder_TRACK)
except:
    print("Already crated the folder?")

cam_id = 0
frameiter = 0

# setup stage
OFM_TO_GRBL_FAC = 1000 # necessary since OFM thinks in steps (int), GRBL in pyhsical coordinates (float)
OFM_TO_GRBL_FAC_Z = 250
PTYCHO_Scalingfactor_coords = 1
ports = list(port_list.comports())
for p in ports:
    print (p)
port =  ports[0].__dict__['device']# 'COM6' # corresponds to the device managers USB Port
board = grbl.grblboard(serialport=port)

# reset stage's position
board.zero_position()

# testing board
# -> 100 steps are ~10 mum

if(0):
	position = (5000,0,0)
	board.move_abs((position[0]/OFM_TO_GRBL_FAC,position[1]/OFM_TO_GRBL_FAC,position[2]/OFM_TO_GRBL_FAC_Z))
	position = (0,0,0)
	board.move_abs((position[0]/OFM_TO_GRBL_FAC,position[1]/OFM_TO_GRBL_FAC,position[2]/OFM_TO_GRBL_FAC_Z))
	position = (0,5000,0)
	board.move_abs((position[0]/OFM_TO_GRBL_FAC,position[1]/OFM_TO_GRBL_FAC,position[2]/OFM_TO_GRBL_FAC_Z))
	position = (0,0,0)
	board.move_abs((position[0]/OFM_TO_GRBL_FAC,position[1]/OFM_TO_GRBL_FAC,position[2]/OFM_TO_GRBL_FAC_Z))


# prepare Ptycho coordinates/header
# open file for getting positions
f = open("Fermat_FOV1mm_step55um_202points.txt", "r")
print(f.readline())       

if(0):
    import h5py
    #ptychogram = [npos,N,N] ,N=number of pixels
    #umPositions_from_encoder = [npos,2] position in meters
    #beam_diameter, approximated size in meters
    wavelength = 450e-9
    Nd = 1
    zo = 30e-3
    beam_diameter = 0
    umPositions_from_encoder

    #ptychogram = [npos,N,N] ,N=number of pixels
    #umPositions_from_encoder = [npos,2] position in meters
    #beam_diameter, approximated size in meters
    with h5py.File(f'fileName.hdf5', 'w') as hf:
        hf.create_dataset('ptychogram', data=ptychogram, dtype='f')
        hf.create_dataset('encoder', data=umPositions_from_encoder, dtype='f') 
        hf.create_dataset('dxd', data=(dxd,), dtype='f')
        hf.create_dataset('Nd', data=(ptychogram.shape[-1],), dtype='i')
        hf.create_dataset('zo', data=(zo,), dtype='f')
        hf.create_dataset('wavelength', data=(wavelength,), dtype='f')
        hf.create_dataset('entrancePupilDiameter', data=(beam_diameter,), dtype='f')
        hf.close()


#setup encoder camera
def gstreamer_pipeline(
    capture_width=640,
    capture_height=480,
    display_width=640,
    display_height=480,
    framerate=60,
    flip_method=0,
):
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )
# To flip the image, modify the flip_method parameter (0 and 2 are the most common)
print(gstreamer_pipeline(flip_method=0))

if(is_calib):
	cap = buffcam.VideoCapture(gstreamer_pipeline(flip_method=0))#, cv2.CAP_GSTREAMER)


# In[7]:

if(is_calib):
	# let the camera warm up
	for _ in range(20):
	    ret_val, img = cap.read()
	    print(np.mean(img))


# # Acquire Ptychograms
iiter = 0
umPositions_from_encoder = []
with Vimba.get_instance():
    with get_camera(cam_id) as cam:

        setup_camera(cam)
        print('Acquiring Background')

        # closing the blind again
        GPIO.output(output_pin, GPIO.HIGH)
        GPIO.output(output_gnd, GPIO.LOW)
        time.sleep(.1)            
        GPIO.output(output_pin, GPIO.LOW)
        GPIO.output(output_gnd, GPIO.LOW)
        time.sleep(.1)            

        myframe = cam.get_frame().as_numpy_ndarray()
        myfilename = mybasepath+myfolder+"/Background.tif"
        tif.imsave(myfilename, myframe) #, imagej=True)
        
        # open the blind again
        GPIO.output(output_pin, GPIO.LOW)
        GPIO.output(output_gnd, GPIO.HIGH)
        time.sleep(.1)            
        GPIO.output(output_pin, GPIO.LOW)
        GPIO.output(output_gnd, GPIO.LOW)
        time.sleep(.1)            
               
        while(True):
            try:
                position = np.float32(np.array((f.readline()).split('\n')[0].split(' ')))*10
                ix,iy = PTYCHO_Scalingfactor_coords*position[0]+offset_x, PTYCHO_Scalingfactor_coords*position[1]+offset_y
                position = (ix,iy,0) 
                umPositions_from_encoder.append((ix,iy))
                board.move_abs((position[0]/OFM_TO_GRBL_FAC,position[1]/OFM_TO_GRBL_FAC,position[2]/OFM_TO_GRBL_FAC_Z))
                time.sleep(.5)
                
                # take a snapshot of the secondary camera for tracking the position
                if(is_calib):
                    _, myimage = cap.read() 
                    myimage = np.mean(myimage,-1)
                    mytrackfilename = mybasepath+myfolder_TRACK+"/track.tif"#_"+str(iiter)+"_ix_"+str(ix)+"iy_"+str(iy)+".tif"
                    #print("Saving: " + mytrackfilename)
                    tif.imsave(mytrackfilename, myimage, append=True) #, imagej=True)
            

                #print('{} acquired {}'.format(cam, frame), flush=True)
                while(True):
                    myframe = cam.get_frame()
                    myframe_np = myframe.as_numpy_ndarray()
                    myfilename = mybasepath+myfolder+"/"+str(iiter)+".tif" #/"+str(iiter)+"_ix_"+str(ix)+"iy_"+str(iy)+".tif"
                    
                    tif.imwrite(myfilename, myframe_np)
                    print("Frame Status:" + str(myframe.get_status()))
                    print("Frame mean:" + str(np.mean(myframe_np)))
                    
                    # check if data has been written to the disk correctly
                    testframe=tif.imread(myfilename)
                    N_pix_dead = np.mean(testframe<=(BLACKLEVEL-20)) # account for noise +/-
                    if  myframe.get_status() == FrameStatus.Complete  and N_pix_dead < 1000:
                        break
                    
                    print("Detected a corrupted frame")

                # save for later
                scaling_factor = .25
                img = cv2.resize(myframe_np, None, fx=scaling_factor, fy=scaling_factor, interpolation=cv2.INTER_AREA)
                tif.imsave( mybasepath+myfolder+"/AllImages.tif", img,append=True)
                
                # not working in threads.. plt.figure(1), plt.imshow(np.squeeze(myframe)), plt.colorbar(), plt.show()
                
                print('Acquired a frame and saved it here: '+myfilename)
                if(is_display):
                    plt.subplot(121)
                    plt.title('Ptychogram')
                    plt.imshow(myframe_np)
                    plt.subplot(122)
                    plt.title('Stage Frame')
                    plt.imshow(myimage)  
                    plt.show()
                    
                iiter += 1
            except Exception as e:
                print(e)
                board.move_abs((0,0,0))
                cam.stop_streaming()
                cap.release()
                board.close()
                break
    board.move_abs((0,0,0))

# finally close the stage and the camera
f.close()
cap.release()
board.close()

