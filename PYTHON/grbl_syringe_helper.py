import numpy as np

class syringe:
    '''
    Syringe	ID (mm)	Area (mm^2)	V/mm (mL)	V/step (mL)	Steps/mL (n)
    1 mL	4.7	17.34944543	0.017349445	4.33736E-06	230554.9198
    5 mL	12.3	118.8228881	0.118822888	2.97057E-05	33663.54801
    10 mL	15.6	191.134497	0.191134497	4.77836E-05	20927.67168
    20 mL	20.1	317.308712	0.317308712	7.93272E-05	12606.0201
    '''

    def __init__(self, board, axis='X', syringe_vol = 1, syringe_d=4.7, microsteps=16, step_angle=1.8):
        # all settings derived from https://github.com/Vsaggiomo/Ender3-syringe-pumps/blob/main/Software/VideoS1.gcode
        print("Initializing syringe "+axis)
        self.board = board
        self.board.speed = 2 # default ?

        self.Stepper_Motor = 'BJ42D15-26V09'
        self.Stepper_Driver = 'TMC2208'
        self.Leadscrew = 0.8 # M5, pitch
        self.microstep = microsteps
        self.step_angle = step_angle
        self.min_movement = 0.8/((360/self.step_angle)*self.microstep) # Min. Movement (mm)	
        

        self.axis = axis
        self.syringe_vol = syringe_vol
        self.syringe_d = syringe_d
        self.steps_to_mm = ((360/self.step_angle)*self.microstep)/self.Leadscrew

        # compute physical properties
        self.syringe_area = np.pi*(self.syringe_d/2)**2 # mm^2
        self.syringe_volume =(np.pi*(self.syringe_d/2)**2)/1000 # V/mm (mL)
        self.ml_per_steps = self.syringe_volume*self.min_movement 
        self.steps_per_ml = 1/self.ml_per_steps

        # write settings above
        self.init_grbl()

        # disable heat control
        self.board._write('M302 S0') # print without checking temperature 
        self.board._write('M211 S0') # print without checking the end stops 


    def init_grbl(self):
        if self.axis == 'X':
            self.axis_mask = (1,0,0)
            self.board.xconfig ={
                # 'steps/mm':360/1.8*diameter/2., #<--resolutoin
                'steps/mm': self.steps_per_ml, #<--resolutoin
                'mm/sec2': 2.0, #<--acceleration
                'mm/min': 10 #<--max speed
                }
        if self.axis == 'Y':
            self.axis_mask = (0,1,0)
            self.board.yconfig ={
                # 'steps/mm':360/1.8*diameter/2., #<--resolutoin
                'steps/mm': self.steps_per_ml, #<--resolutoin
                'mm/sec2': 2.0, #<--acceleration
                'mm/min': 10 #<--max speed
                }
        if self.axis == 'Z':
            self.axis_mask = (0,0,1)
            self.board.zconfig ={
                # 'steps/mm':360/1.8*diameter/2., #<--resolutoin
                'steps/mm': self.steps_per_ml, #<--resolutoin
                'mm/sec2': 2.0, #<--acceleration
                'mm/min': 10 #<--max speed
                }

        print("Config saved")
        self.board.write_all_settings()
        print("Config wrote")


    def dispense(self, d_volume, blocking=True):
        self.board.move_rel(np.array(self.axis_mask)*d_volume, blocking=True)

    def aspirate(self, a_volume, blocking=False):
        self.board.move_rel(np.array(self.axis_mask)*a_volume, blocking=True)
        
    def home(self, steps=10):
        pass # not implemented yet