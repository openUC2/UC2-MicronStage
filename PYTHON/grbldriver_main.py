# -*- coding: utf-8 -*-
"""
Created on Fri Jun 25 11:19:06 2021

@author: diederichbenedict
"""
print("Programme started!")
import grbldriver as grbldriver # library for the xy arm

port = "COM10"
board = grbldriver.GrblDriver(port)
print("Board conected.")

board.write_global_config()
board.reset_stage()
# board.is_debug=True

#%%

stpsmm = 16250

board.xconfig ={
            # 'steps/mm':360/1.8*diameter/2., #<--resolutoin
            'steps/mm':stpsmm, #<--resolutoin
            'mm/sec2': 100.0, #<--acceleration
            'mm/min': 10 #<--max speed
            }
board.yconfig ={
            'steps/mm':stpsmm, #<--resolutoin
            'mm/sec2': 100.0, #<--acceleration
            'mm/min': 10 #<--max speed
            }

board.zconfig ={
            'steps/mm':stpsmm, #<--resolutoin
            'mm/sec2': 1000.0, #<--acceleration
            'mm/min': 10 #<--max speed
            }


print("Config saved")
board.write_all_settings()
print("Config wrote")


#%%
board.move_rel((-100,-100,00), wait_until_done=True)


#%%
board.move_rel((0,0,1000), wait_until_done=True)