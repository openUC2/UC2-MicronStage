import time
import serial
import numpy as np
import fnmatch
import re

'''
All available GRBL Codes:
$0 = 10    (Step pulse time, microseconds)
$1 = 1    (Step idle delay, milliseconds)
$2 = 0    (Step pulse invert, mask)
$3 = 0    (Step direction invert, mask)
$4 = 0    (Invert step enable pin, boolean)
$5 = 0    (Invert limit pins, boolean)
$6 = 0    (Invert probe pin, boolean)
$10 = 1    (Status report options, mask)
$11 = 0.010    (Junction deviation, millimeters)
$12 = 0.002    (Arc tolerance, millimeters)
$13 = 0    (Report in inches, boolean)
$20 = 0    (Soft limits enable, boolean)
$21 = 0    (Hard limits enable, boolean)
$22 = 0    (Homing cycle enable, boolean)
$23 = 0    (Homing direction invert, mask)
$24 = 25.000    (Homing locate feed rate, mm/min)
$25 = 500.000    (Homing search seek rate, mm/min)
$26 = 250    (Homing switch debounce delay, milliseconds)
$27 = 1.000    (Homing switch pull-off distance, millimeters)
$30 = 1000    (Maximum spindle speed, RPM)
$31 = 0    (Minimum spindle speed, RPM)
$32 = 0    (Laser-mode enable, boolean)
$100 = 640.000    (X-axis travel resolution, step/mm)
$101 = 640.000    (Y-axis travel resolution, step/mm)
$102 = 100.000    (Z-axis travel resolution, step/mm)
$110 = 500.000    (X-axis maximum rate, mm/min)
$111 = 500.000    (Y-axis maximum rate, mm/min)
$112 = 500.000    (Z-axis maximum rate, mm/min)
$120 = 1.000    (X-axis acceleration, mm/sec^2)
$121 = 1.000    (Y-axis acceleration, mm/sec^2)
$122 = 1000.000    (Z-axis acceleration, mm/sec^2)
$130 = 200.000    (X-axis maximum travel, millimeters)
$131 = 200.000    (Y-axis maximum travel, millimeters)
$132 = 200.000    (Z-axis maximum travel, millimeters)


For the 28byj motor:
http://www.robotmaker.eu/ROBOTmaker/arduino-control-of-stepper-morot
Connecting 28BYJ-48 directly to Arduino UNO CNC Shield using GRBL:
1 ->Pink
2 -> Orange
3 -> Red
4 ->Blue

Commands: for Z-axis
    $102=32768      # Z Axis steps/mm. 32768 is 8*4096.which will give you 1 rev per millimeter, which needs to be adjusted depending on your own belt or geared setup accordingly. 
    $112 = 100.     # Z Axis maximim velocity (mm/min) 
    $122 = 20       # Z-Axis Acceleration (mm/sec2) 
'''
class grblboard:
    is_cellstorm = True

    currentposition = (0,0,0) # XYZ
    zero_coordinates = currentposition
    backlash = 0

    # 
    steps_per_mm_x = 640 # how many revolution per fiven distnace => steps/mm
    steps_per_mm_y = 640 # Steps-per-Revolution*microsteps/mm per revolution
    steps_per_mm_z = 64 # 320 # in our case: 200*16*2mm= 6400
    if is_cellstorm: steps_per_mm_z = 3276.8

    # accellation for motors
    accel_x = 1 # 15
    accel_y = 1 # 15 # 
    accel_z = 1
    if is_cellstorm: 
        accel_x = 20
        accel_y = 20
        accel_z = 20

    maxspeed_x = 100.
    maxspeed_y = 100.
    maxspeed_z = 100.

    if is_cellstorm: 
        idletime = 1 # 255 # means infinity wait time
        maxspeed_z = 1000
    else: idletime = 255 
    
    board = 'GRBL'
    firmware = 'DEFAULT'
    position = [0,0,0] # xyz
    speed = 50
    speed_z = 50

    laser_intensity = 0
    led_state = 0
    
    

    



    def __init__(self, serialport = "/dev/ttyUSB0",
                 currentposition=currentposition, backlash=backlash):

        self.backlash = backlash
        
        print('Initializing XYZ-stepper')
        try:
            self.serial_xyz = serial.Serial(serialport,115200,timeout=1) # Open grbl serial port
        except:
            available_ports = self.auto_detect_serial_unix()
            serialport = serial.Serial(available_ports[0], 115200,timeout=1)

        self.initserial()

    def close(self):
        """ CLose Serial Connection"""
        self.serial_xyz.close()

    def initserial(self):
        """ Initiliazing the serial connection and set home coordinates """
        self.sendgrbl("\r\n\r\n") # Wake up grbl
        time.sleep(2)   # Wait for grbl to initialize 
        self.sendgrbl("$$") # Soft reset
        self.sendgrbl("$X") # Soft reset
        self.sendgrbl("$10=2")
        self.sendgrbl("$3=3")
        self.sendgrbl("$22=0") # disable homing on startup
        self.sendgrbl("$21=0") # disable hard limits
        self.sendgrbl("$20=0") # disable soft limits
        self.sendgrbl("$27=1.000") # Homing Pull-off (mm)
        time.sleep(1)
        self.resethome()                # reset the boards coordinates to 0,0,0
        self.setphysicalcoords()        # turns per mm
        self.currentposition = self.getcurrentpos()
        self.zero_coordinates = self.currentposition
        self.set_units()                # mm or inches?
        self.setaccellaration()         # limit maximum accellaration
        self.setspeed()
        self.setideltime()
        self.set_laser_intensity(0)
        self.set_led(0)

    def zero_position(self):
        self.resethome()
        self.currentposition=self.getcurrentpos()

    def auto_detect_serial_unix(self, preferred_list=['*']):
        '''try to auto-detect serial ports on posix based OS'''
        import glob
        glist = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        ret = []

        # try preferred ones first
        for d in glist:
            for preferred in preferred_list:
                if fnmatch.fnmatch(d, preferred):
                    #ret.append(SerialPort(d))
                    ret.append(d)
        if len(ret) > 0:
            return ret
        # now the rest
        for d in glist:
            #ret.append(SerialPort(d))
            ret.append(d)
        return ret

    def setideltime(self):
        self.sendgrbl('$1='+str(self.idletime)) # default: 314.961 #,x step/mm) 

    def setspeed(self):
        self.sendgrbl('$110='+str(self.maxspeed_x)) # default: 50.000
        self.sendgrbl('$111='+str(self.maxspeed_y)) # default:
        self.sendgrbl('$112='+str(self.maxspeed_z)) # default:

    def setaccellaration(self):
        self.sendgrbl('$120='+str(self.accel_x)) # default: 50.000
        self.sendgrbl('$121='+str(self.accel_y)) # default:
        self.sendgrbl('$122='+str(self.accel_z)) # default:

    def setphysicalcoords(self):
        self.sendgrbl('$100='+str(self.steps_per_mm_x)) # default: 314.961 #,x step/mm) 
        self.sendgrbl('$101='+str(self.steps_per_mm_y)) # default: 314.961 #,y step/mm) 
        self.sendgrbl('$102='+str(self.steps_per_mm_z)) # default: 314.961 #,z step/mm) 

    def resethome(self):
        self.sendgrbl("G10 L20 P1 X0 Y0 Z0")
        self.sendgrbl("G10 P0 L20 X0 Y0 Z0")
        print('myhome is: '+str(self.getcurrentpos()))

    def getcurrentpos(self):
        poslist = self.sendgrbl("?").split('WPos')[-1].split('|')[0].split(',')
        try:
            posx, posy, posz = float(poslist[0]),float(poslist[1]),float(poslist[2])
        except:
            try:
                poslist = re.split(',|:',re.split('WPos|MPos', self.sendgrbl("?"))[-1].split('|')[0])[1:4]
                posx, posy, posz = float(poslist[0]),float(poslist[1]),float(poslist[2])
            except:
                # revert to old position and force flushing the serial once again
                posx, posy, posz = self.currentposition[0], self.currentposition[1], self.currentposition[2]
            self.serial_xyz.flushInput()
            
        return (posx, posy, posz)

    def sendgrbl(self, cmd="?"):
        #print(cmd)
        self.serial_xyz.write((cmd + '\n').encode())
        time.sleep(0.1)
        # message from the GRBL board:
        return_message = ''
        #while not b'ok\r\n'==self.serial_xyz.readline():
        grbl_out = self.serial_xyz.readline() # Wait for grbl response with carriage return
        return_message = (grbl_out.strip()).decode()
        self.serial_xyz.flushInput() 
        return return_message
        
    def move_rel(self, position=(0,0,0)):
        time.sleep(1)
        return self.go_to(position[0], position[1], position[2], 'rel')

    def move_abs(self, position=(0,0,0)):
        #time.sleep(1)
        return self.go_to(position[0], position[1], position[2], 'abs')

    def set_units(self, is_metric=True):
        if is_metric:
            cmd='$13=0' #  for mm
            self.sendgrbl(cmd)
        else:
            cmd='$13=1' #  for inches
            self.sendgrbl(cmd)

    def go_to(self, pos_x=0, pos_y=0, pos_z=0, mode='abs'):
 #       self.mystepstogo = (pos_x, pos_y)-self.currentposition        
        # Stream g-code to grbl
        g_dim = "G21"                           # This measures Metric 
        g_dist = "G90"
        ''' obsolote with the mode==rel condition below
        if mode=="abs": 
            g_dist = "G90"                          # G91 is for incremental, G90 is for absolute distance
        elif mode == 'rel':
            g_dist = "G91"
        '''
        g_dist = "G90"                          # G91 is for incremental, G90 is for absolute distance
        # steps to go:
        
        old_position = self.currentposition

        # set speed
        g_speed = "F"+format(self.speed, '.10f')#

        # construct command string
        cmd = g_dim + " " + g_dist 

        # super weird hack around - only to make OFM happy
        if mode == 'rel':
            # calculate difference coordinates where you want to go
            togo_x = (old_position[0]+pos_x)
            togo_y = (old_position[1]+pos_y)
            togo_z = (old_position[2]+pos_z)
            wait_loop = np.max((abs(pos_x),abs(pos_y),abs(pos_z)))*3# define a wait threshold until the loop below should break without reaching the final position

        elif mode == 'abs': # remember: We are always in absolute coordinates!!
            togo_x = pos_x 
            togo_y = pos_y
            togo_z = pos_z
            wait_loop = np.max((abs(old_position[0]-pos_x), abs(old_position[1]-pos_y), abs(old_position[2]-pos_z)))*3 # define a wait threshold until the loop below should break without reaching the final position

        # construct command string
        if not togo_x == old_position[0]: 
            cmd += "X"+str(togo_x) 
        if not togo_y == old_position[1]: 
            cmd += "Y"+str(togo_y) 
        if not togo_z == old_position[2]: 
            cmd += "Z"+str(togo_z) 
            g_speed = "F"+format(self.speed_z, '.10f')#    

        # finalize string
        cmd += " " + g_speed

        # message from the GRBL board:
        return_message = self.sendgrbl(cmd)

        #%% Make sure the destination is reached
        t1 = time.time()
        diffx, diffy, diffz = 0,0,0
        while(True): 
            # read position list
            pos_x_current, pos_y_current, pos_z_current = self.getcurrentpos()
            
            # onyl check the difference if there is a motion in this direction
            if(cmd.find('X')>=0): diffx = togo_x - pos_x_current
            if(cmd.find('Y')>=0): diffy = togo_y - pos_y_current
            if(cmd.find('Z')>=0): diffz = togo_z - pos_z_current 
            '''
            elif(mode=='abs'):
                diffx = old_position[0]+togo_x - pos_x_current
                diffy = old_position[1]+togo_y - pos_y_current
                diffz = old_position[2]+togo_z - pos_z_current 
            '''
            if(0):
                print('x: '+str(diffx) + ', y: '+str(diffy) + ', z: '+str(diffz))

            if(abs(diffx)<.01 and 
                abs(diffy)<.01 and
                abs(diffz)<.01):
                break

            if abs(time.time()-t1)>wait_loop:
                print("Not reaching limit yet..")# timelimit reached
                print('DIFF: x: '+str(diffx) + ', y: '+str(diffy) + ', z: '+str(diffz))
                break            
        #%%
        self.currentposition =  self.getcurrentpos()

        return return_message


    def set_laser_intensity(self, intensity):
        self.laser_intensity = intensity
        if self.led_state:
            prefix = "M4"
        else:
            prefix = "M3"
        
        cmd =  "G21 G90 " + prefix+" S"+str(self.laser_intensity)
        return self.sendgrbl(cmd)

    def set_led(self, state=1):
        # state is either 1 or 0
        self.led_state = state
        if self.led_state:
            prefix = "M4"
        else:
            prefix = "M3"
        
        cmd =  "G21 G90 " + prefix + " S"+str(self.laser_intensity)
        return self.sendgrbl(cmd)
