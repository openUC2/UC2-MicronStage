# -*- coding: utf-8 -*-
"""
Created on Fri Jun 25 11:19:06 2021

@author: diederichbenedict
"""
import grbldriver as grbldriver # library for the xy arm
import grbl_syringe_helper as gsh

port = "COM10"
board = grbldriver.GrblDriver(port)
print("Board connected.")

# init the board
board.globalconfig={} # don't write any default grlb settings!!
board.write_global_config()
board.reset_stage()
board.is_debug=True

#%%
syringe_x = gsh.syringe(board, axis='X', syringe_vol = 1, syringe_d=4.7, microsteps=16, step_angle=1.8)
syringe_x.dispense(100)
syringe_x.aspirate(100)


stpsmm = 16250

board.xconfig ={
            # 'steps/mm':360/1.8*diameter/2., #<--resolutoin
            'steps/mm':stpsmm, #<--resolutoin
            'mm/sec2': 2, #<--acceleration
            'mm/min': 10 #<--max speed
            }
board.yconfig ={
            'steps/mm':stpsmm, #<--resolutoin
            'mm/sec2': 2, #<--acceleration
            'mm/min': 10 #<--max speed
            }

board.zconfig ={
            'steps/mm':stpsmm, #<--resolutoin
            'mm/sec2': 2, #<--acceleration
            'mm/min': 10 #<--max speed
            }


print("Config saved")
board.write_all_settings()
print("Config wrote")


#%%
board.move_rel((-100,-100,00), wait_until_done=True)


#%%
board.move_rel((0,0,1000), wait_until_done=True)