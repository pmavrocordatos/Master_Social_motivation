#!/usr/bin/env python3 **
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  6 08:37:17 2023
@author: psyteam74
Last update: 17-05-2024
"""
######################## IMPORTS ######################## 
import pygame
import time
from datetime import datetime
import csv
import os
import sys
import threading
import random
import numpy as np
#from threading import Event
from random import seed
#from random import randint
#from numpy import isnan
import ModularStuffBoard_2302_01
import glob
#import serial.tools.list_ports
#import pdb

######################## SYSTEM INITIATION ######################## 
print("Hope you performed a reset of all the hardware and the kernel before launching the task !!!")
# Exit = int(input("So, reset done (1) or not (0): "))
Exit = 1
if Exit == 0:
    print("\nExiting the task... Reset the hardware and the kernel !!!")
    sys.exit()

# Serial ports handler
my_ports = glob.glob ('/dev/tty[A-Za-z]*')
myBox = ModularStuffBoard_2302_01.netBox(my_ports[0], 115200)

if myBox is None:
    print("ABORT, device not connected")

# Modules connection
else:
    # CONFIGURE THE BOX WITH THE MODULES IN USE (change adress if necessary)
    # Camera module
    cams = ModularStuffBoard_2302_01.camTracking(myBox, 0x56)
    
    # Feeder module
    feeder1 = ModularStuffBoard_2302_01.feeder(myBox, 0x51)
    
    # Create a new feeder module in the box with I2C adress
    feeder2 = ModularStuffBoard_2302_01.feeder(myBox, 0x59)
    
    # Weight sensor module
    weight1 = ModularStuffBoard_2302_01.weightMeasurement(myBox, 0x52)
    
    # Stepper module
    doors1 = ModularStuffBoard_2302_01.dualStepper(myBox, 0x58)
    
######################## Modular doors setting ######################## a
#usr_speed = input("Put desired speed (recomanded = 90)")
usr_speed = "95"
doors1.setDoorSpeed(0, int(usr_speed, 10))
doors1.setDoorSpeed(1, int(usr_speed, 10))

##nd###################### MOUSE INFO: ######################## 
MouseID = input("\nMouse ID: ")
MouseDoB = input("Date of birth (YYYYMMDD): ")
#isKO = input("Is it a LgDel mouse (1 = yes / 0 = no): ")
# stimSide = int(input("The stim mouse is placed left (0) or right (1): "))
# socialRewardStim = int(input("The visual stimulus associated with the social reward is the grid (0) or the lines (1): "))
# Start_date = time.strftime('%d-%m-%Y %H:%M:%S')

#MouseID = 1
#MouseDoB = 1
isKO = 0
stimSide = 1
socialRewardStim = 1

Start_date = time.strftime('%d-%m-%Y %H:%M:%S')

######################## DATA FOLDER ######################## 
Data_folder = 'Data/' + time.strftime('%Y-%m-%d') + '_Mouse-' + str(MouseID)
if not os.path.exists(Data_folder):
    os.makedirs(Data_folder)

######################## NIGHT PERF MONITORING STUFF ######################## 
def findMiddle(input_list):
    middle = float(len(input_list))/2
    if middle % 2 != 0:
        return input_list[int(middle - .5)] # take into account that a list start with 0
    else:
        return (input_list[int(middle)]) # if the list has a pair number of elements the returned value is the one after the middle one

######################## PYGAME INITIATION ######################## 
pygame.init() 
screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
pygame.display.set_caption('EcoBox Test')
pygame.mouse.set_visible(0)

# Images importation
grid = pygame.image.load("Img/grid.png").convert()
line = pygame.image.load("Img/line.png").convert()
white = pygame.image.load("Img/white.png").convert()
black = pygame.image.load("Img/black.png").convert()

# Get image size
grid_size = grid.get_size()
line_size = line.get_size()
blink_size = white.get_size()
screen_size = screen.get_size()

# Define scale
scale = 1.4

# Put image at scale
grid = pygame.transform.scale(grid, (grid_size[0]*scale, grid_size[1]*scale))
line = pygame.transform.scale(line, (line_size[0]*scale, line_size[1]*scale))
white = pygame.transform.scale(white, (blink_size[0]*scale, blink_size[1]*scale))
black = pygame.transform.scale(black, (blink_size[0]*scale, blink_size[1]*scale))

# Get scaled image size
grid_size = grid.get_size()
line_size = line.get_size()
blink_size = white.get_size()

######################## MODULE SETTINGS ######################## 
lat_time = 0.2
##LED SETTING (day setting)##
cams.setLight(0, 1)
time.sleep(lat_time)
cams.setLight(1, 0)
time.sleep(1)   

# Zone definition (interaction and bedding)
JuvDoorZone = lambda: cams.getZoneStates(1)[abs(stimSide-1)]
JuvDoorState = JuvDoorZone()
time.sleep(lat_time)

ObjDoorZone = lambda: cams.getZoneStates(1)[stimSide]
ObjDoorState = ObjDoorZone()
time.sleep(lat_time)

BeddingZone = lambda: cams.getZoneStates(1)[3]
BeddingState = BeddingZone()
time.sleep(lat_time)

JuvDoorStimZone = lambda: cams.getZoneStates(0)[0] # Carefull if we have a camera in each stim side! (correct with stim side etc...)
JuvDoorStimState = JuvDoorStimZone()

ObjDoorStimZone = True # We dont have a second camera for the stim object side (to transform into function if a second camera is installed -> check call into tasks)

##WEIGHT SENSORS##
weight1.disableSensor(0) #turns off bottle weight measurement
time.sleep(lat_time)

Task_start = int(time.time())
#############THREAD#############

print("Task start: ",Task_start)

#now = datetime.now()
dark = 0

class Hardware(threading.Thread): # monitoring and hardware control
    #def __init__(self, event):
    def __init__(self):   
        threading.Thread.__init__(self)
        # self.daemon = True
        #self.event = event
        self.flag = False
        # self.lock = threading.Lock()
        self.stop_control = False
        self.bedding_zone = False
        self.door_open_NS = False
        self.door_close_NS = False # at the beggining doors are closed
        self.door_open_S = False
        self.door_close_S = False
        
    def reset_flag(self):
        self.flag = True
           
    def stop(self):
        self.stop_control = True
        
    def set_door_open_NS(self):
        self.door_open_NS = True
        
    def set_door_close_NS(self):
        self.door_close_NS = True
        
    def set_door_open_S(self):
        self.door_open_S = True
        
    def set_door_closed_S(self):
        self.door_close_S = True
    
    def set_doors_open(self):
        self.door_open_NS = True
        self.door_open_S = True
        
    def set_doors_closed(self):
        self.door_close_NS = True
        self.door_close_S = True
        
    def actuate_zones(self):
        # Actuate zones and set respective states
        global JuvDoorState
        JuvDoorState = JuvDoorZone()
        time.sleep(lat_time)
        global ObjDoorState
        ObjDoorState = ObjDoorZone()
        time.sleep(lat_time)
        global JuvDoorStimState
        JuvDoorStimState = JuvDoorStimZone()
        time.sleep(lat_time)
        global BeddingState
        BeddingState = BeddingZone()
        time.sleep(lat_time)
        
      
            
    def run(self):
        # Names columns
        headerM = ['Timestamp', 'Mouse_weight', 'Mouse_weight_since','Pellets_consumed'] #['Timestamp', 'Mouse_weight', 'Mouse_weight_since', 'Bottle_weight', 'Bottle_weight_since','Pellets_consumed']
        Mouse_weight = float(input("\nMouse weight [g]: "))
        first_measure = True
        Mouse_weight_since = 0
        #Bottle_weight = 0
        previous_bedding = 0
        #previous = 0
        Pellets_consumed = 0
        Pellets_consumed_stim = 0
        Mouse_weight_array = []
        #Bottle_weight_array = []
        time_to_measure_weight = 30 # the time for the balance to take a weight measure 30 sec after start 
        current_tare = int(time.time())
        last_tare = 0 # so taring occurs at the beginning of the task
        miscalib_count = 0
        ongoing_trial = False
        dark = 0
        
        # Creates rows of information about the mouse (ID, DoB, isKO) and position of the stim mice.
        with open(Data_folder + '/Monitoring.csv', 'w', encoding='utf-8') as fileM:
            writerM = csv.writer(fileM)
            writerM.writerow([Start_date])
            writerM.writerow('')
            writerM.writerow(['Mouse ID: ', MouseID])
            writerM.writerow(['DoB: ', MouseDoB])
            writerM.writerow(['isKO (1 = LgDel): ', isKO])
            writerM.writerow(['Stim side (1 = right): ', stimSide])    
            writerM.writerow('') #Creates all the columns of the monitoring csv. The columns will be filled with values at every timestamp
            writerM.writerow(headerM)
           
        while going:
            #print(BeddingState)
            ### Zone variable actuation ###
            self.actuate_zones()
            
            ### Monitor if a trial is ongoing ### use this variable to avoid confilct with other commands
            
            #print(ongoing_trial)
            
            ## Feeder actuation ##
            feederstate1 = feeder1.getPelletSensorState()
            if feederstate1 == 0 and not ongoing_trial:
                time.sleep(lat_time)
                feeder1.setPellet(1)
                Pellets_consumed += 1
                print(Pellets_consumed," pellet eaten (test mouse)") 
            
            time.sleep(lat_time)
            
            feederstate2 = feeder2.getPelletSensorState()
            if feederstate2 == 0 and not ongoing_trial:
                time.sleep(lat_time)
                feeder2.setPellet(1)
                Pellets_consumed_stim +=1
                print(Pellets_consumed_stim," pellet eaten (stim mouse)") 
                
            ###  Time actuation ###
            now = datetime.now()
            
            if now.hour >= 8  and now.hour < 20: #modify this!!!
                if dark == 1:
                    dark = 0
                    time.sleep(lat_time)
                    cams.setLight(0, 1)
                    time.sleep(lat_time)
                    cams.setLight(1, 0) #DAY
                    time.sleep(lat_time)
                    myModules.reset_flag()
                    print("Day")
            else:
                if dark == 0:
                    dark = 1
                    time.sleep(lat_time)
                    cams.setLight(0, 0)
                    time.sleep(lat_time)
                    cams.setLight(1, 1) #NIGHT
                    time.sleep(lat_time)
                    #myModules.reset_flag()
                    print("Night")

            # # code to test the day/night switch (every minute)
            # if now.minute % 2 == 0:
            #     if dark == 1:
            #         dark = 0
            #         cams.setLight(0, 1)
            #         time.sleep(lat_time)
            #         cams.setLight(1, 0) #DAY
            #         time.sleep(lat_time)
            #         myModules.reset_flag()
            #         print("dark is: ", dark, " time is: ", now.minute)
            # else:    
            #     if dark == 0:
            #         dark = 1
            #         time.sleep(lat_time)
            #         cams.setLight(0, 0)
            #         time.sleep(lat_time)
            #         cams.setLight(1, 1) #NIGHT
            #         time.sleep(lat_time)
            #         print("dark is: ", dark, " time is: ", now.minute)
                        
            ## Stop control of the thread ###
            if self.stop_control:
                break
            
            time.sleep(lat_time)
            
            current_tare = int(time.time())
            
            if current_tare - last_tare > 7200 or miscalib_count >= 3: # faire une tare toutes les 2h
                if not (ongoing_trial or BeddingState):
                    weight1.startTare(1) #tare mouse bedding
                    time.sleep(5)
                    last_tare = current_tare
                    miscalib_count = 0
                    print("A tare was done", time.time())
                else:
                    print("Waiting for the mouse to get out of the nest...")
                    
            # Open Non social open
            if self.door_open_NS: #and not self.door_close_NS:
                doors1.setDoorState(int(not stimSide), 1) #door open 
                ongoing_trial = True
                self.door_open_NS = False
                time.sleep(lat_time)
            
            #Open Social
            if self.door_open_S: #and not self.door_close_S:
                doors1.setDoorState(stimSide, 1) #door  open
                ongoing_trial = True
                self.door_open_S = False
                time.sleep(lat_time)
            
            # Close Non social    
            if self.door_close_NS: #and not self.door_open_NS:
                doors1.setDoorState(int(not stimSide), 0) #door closed
                ongoing_trial = False
                self.door_close_NS = False
                time.sleep(lat_time)
            
            # Close social
            if self.door_close_S: #and not self.door_open_S:
                doors1.setDoorState(stimSide, 0) #closed
                ongoing_trial = False
                self.door_close_S = False
                time.sleep(lat_time)
                    
            if BeddingState:
                if not ongoing_trial: # mouse in nest -> start measure but not during a trial
                    
                    TimestampBedding = int(time.time())-Task_start
                    if TimestampBedding - previous_bedding > time_to_measure_weight: # when the mouse is in the bedding, if weight was taken 
                        previous_bedding = TimestampBedding
                        weight1.startWeightMeasure(1)
                        time.sleep(lat_time)
                        current_weight = weight1.getWeight(1)[0]
                        time.sleep(lat_time)
                        if Mouse_weight*0.9 < current_weight < Mouse_weight*1.10:
                            Mouse_weight_array.append(current_weight)   
                            print("mouse weight measure taken: ", Mouse_weight_array[-1])
                            time_to_measure_weight = 300 #every 5 minutes
                            first_measure = False
                            miscalib_count = 0
                        else:
                            time_to_measure_weight = 5
                            miscalib_count += 1
                            print("scale miscalibrated (miscalib count = ", miscalib_count,")")
                           
                        '''   
                        time.sleep(lat_time)
                        weight1.startWeightMeasure(0)
                        time.sleep(lat_time)
                        current_bottle_weight = weight1.getWeight(0)[0]
                        Bottle_weight_array.append(current_bottle_weight)
                        '''

                        #print("bottle weight measure taken: ", Bottle_weight_array[-1])
                        print(now)
                        
            time.sleep(lat_time)
            
            if self.flag:
                if len(Mouse_weight_array) != 0:
                    TimestampBis = int(time.time())-Task_start
                    time.sleep(lat_time) 
                    #Pellets_consumed = feeder1.getTotalFeed() #function don't work
                    time.sleep(lat_time)
                    print("pellets consumed: ", Pellets_consumed)
                    feeder1.initTotalFeed(0)
                    
                    Mouse_weight = sum(Mouse_weight_array)/len(Mouse_weight_array)
                    print("Mean of mouse weight measures taken: ", Mouse_weight, "from: ",Mouse_weight_array)
                    Mouse_weight_array = []
                    
                    # Bottle_weight = sum(Bottle_weight_array)/len(Bottle_weight_array)
                    # print("mean of bottle weight measures taken: ", Bottle_weight, "from: ", Bottle_weight_array) 
                    print(now)
                    ### time since last measure ###
                    Mouse_weight_since = int(time.time()) - previous_bedding # weight1.getWeight(1)[1]
                    
                    time.sleep(lat_time)
                    # Bottle_weight_since = weight1.getWeight(0)[1]
                    dataM = [TimestampBis, Mouse_weight, Mouse_weight_since, Pellets_consumed]#[TimestampBis, Mouse_weight, Mouse_weight_since, Bottle_weight, Bottle_weight_since, Pellets_consumed]
                    Pellets_consumed = 0
                    Pellets_consumed_stim = 0
                    with open(Data_folder + '/Monitoring.csv', 'a') as fileM: # write the actual csv
                        writerM = csv.writer(fileM)
                        writerM.writerow(dataM)
                        #Bottle_weight_array = []
                    self.flag = False
            
                elif first_measure == True:
                    print("First measure still not taken")
                    self.flag = False
                    
                else:
                    print("No measure was taken before reset_flag(), check that the weight module is operating correctly")
                    self.flag = False
    
                
## THREADING INITIATION ##
myModules = Hardware()
myModules.start()

######################## LAUNCHING THE TASK ######################## 
going = True
timeout = True
stage = 1      # First stage to run
consecutive_success = 10 # number of consecutive success (switch from stages 1 to 2 and 2 to 3): should be set to 10
count = 0
margin = 200
event_list = []
screen.fill(0)

class perf(): # master structure for some variables
    pass
p = perf() 
pygame.display.flip()

pygame.event.clear()

print("\n-> Running the task baby !!\n")


    
######################## GAME LOOP ################################################ GAME LOOP ########################
try:
    while going:
        now = datetime.now()
        key = pygame.key.get_pressed()
        
        ######################## STAGE 1 ########################
        # In this stage, the mouse just has to learn that when she touches the screen, it opens a door
        if stage == 1:
            count = 0   
            header = ['Timestamp', 'Success', 'Elapsed_time', 'Night'] # set the column names
            Timestamp = 0
            Success = 0
            Elapsed_time = 0
            now = datetime.now()
    
            ######################## UPDATE DATA FOLDER ########################
            with open(Data_folder + '/stage1.csv', 'w') as file: # creates csv file
                # insert all the mouse data
                writer = csv.writer(file)
                writer.writerow([Start_date])
                writer.writerow('')
                writer.writerow(['Mouse ID: ', MouseID])
                writer.writerow(['DoB: ', MouseDoB])
                writer.writerow(['isKO (1 = LgDel): ', isKO])
                writer.writerow(['Stim side (1 = right): ', stimSide])    
                writer.writerow('')
                writer.writerow(header)
                
            ######################## STAGE 1 GAME LOOP ######################## 
            while stage == 1:
                
                now = datetime.now()
                
                # Update night/day also in this thread for data storage
                if now.hour >= 8  and now.hour < 20: #modify this !!!
                    if dark == 1:
                        dark = 0
                        
                else:
                    if dark == 0:
                        dark = 1
                        
                # # code to test the day/night switch (every two minutes)
                # if now.minute % 2 == 0:
                #     if dark == 1:
                #         dark = 0
                        
                # else:    
                #     if dark == 0:
                #         dark = 1
                        
                if not myModules.is_alive():
                    print("Thread stoped running at: ", now)
                    break
                    
                for e in pygame.event.get():
                    if e.type == pygame.FINGERDOWN: 
                            event_list.append(["Touched at", now.hour, now.minute, now.second])
                            print("Mouse clicked on screen, starts trial", str(count+1))
                            start = time.time()
                            Timestamp = start - Task_start 
                            myModules.set_doors_open()
                            timeout = False
                            while timeout == False:
                                now = datetime.now()
                                #event_list.append(e)
                                end = time.time()
                                screen.blit(white, (0, screen_size[1]-blink_size[1])) # the screens show white squares, the mouse has to go to the interaction zone 
                                screen.blit(white, (screen_size[0]-blink_size[0], screen_size[1]-blink_size[1]))
                                pygame.display.flip() 
                                time.sleep(0.25) 
                                screen.fill(0)
                                pygame.display.flip()
                                time.sleep(0.25)
                                if (JuvDoorState or ObjDoorState): # if mouse goes to an interaction zone
                                    if end - start < 15:
                                        count += 1 
                                        print("Mouse in interaction zone in good timing ")
                                        Success = 1
                                    Elapsed_time = end - start # duration of the trial is registered
                                    time.sleep(7)
                                    pygame.event.clear() # avoid lunching multiple trials by multiple press
                                    myModules.set_doors_closed()
                                    timeout = True # the mouse is in the interaction zone, the door will close in 7 seconds
                                
                                if end - start >= 15:
                                    print("Mouse failed going to the interaction zone: count trial reset to 0")
                                    pygame.event.clear()
                                    myModules.set_doors_closed()
                                    count = 0 # the trial count stays at zero
                                    Success = 0
                                    Elapsed_time = np.nan
                                    timeout = True
                                    
                            data = [Timestamp, Success, Elapsed_time, dark] # collect data
                            with open(Data_folder + '/stage1.csv', 'a') as file: # write data in the file
                                writer = csv.writer(file)
                                writer.writerow(data)
                            if count == consecutive_success: # the number of success is defined at the start of the code (5)
                                print("Mouse succeded stage, switch to stage ", str(stage + 1))
                                screen.fill(0) # screen black
                                pygame.display.flip()
                                pygame.event.clear()
                                time.sleep(2)
                                stage = 2 # switch to stage 2
                            
                
                        
        ######################## STAGE 2 ########################             
        if stage == 2:
            count = 0
            Timestamp = 0
            Trial = 0
            Touched = 0
            Success = 0
            init_to_touch = 0  
            touch_to_reward = 0
            header = ['Timestamp', 'Trial', 'Touched', 'Success', 'Init2touch', 'Touch2reward']
            with open(Data_folder + '/stage2.csv', 'w') as file: # initiate csv writing and stores mouse infos
                writer = csv.writer(file)
                writer.writerow([Start_date])
                writer.writerow('')
                writer.writerow(['Mouse ID: ', MouseID])
                writer.writerow(['DoB: ', MouseDoB])
                writer.writerow(['isKO (1 = LgDel): ', isKO])
                writer.writerow(['Stim side (1 = right): ', stimSide])    
                writer.writerow('')
                writer.writerow(header)
            ######################## STAGE 2 GAME LOOP ######################## 
            while stage == 2:
                
                now = datetime.now()
                
                if now.hour >= 8  and now.hour < 20:
                    if dark == 1:
                        dark = 0
                        
                else:
                    if dark == 0:
                        dark = 1
                
                if not myModules.is_alive():
                    print("Thread stoped running at: ", now)
                    break
                
                if  (JuvDoorState == 1 or ObjDoorState == 1): 
                    print("Mouse in interaction zone, starts trial ", str(count + 1))
                    start = time.time() # start time as soon as the mouse is on the zone
                    Timestamp = start-Task_start # time relative to very beginning
                    Trial += 1 
                    timeout = False
                    screen.blit(white, (0, screen_size[1]-blink_size[1]))  # the screen show white images
                    screen.blit(white, (screen_size[0]-blink_size[0], screen_size[1]-blink_size[1])) # the screen show white images
                    pygame.display.flip()
                    pygame.event.clear()
                    while timeout == False:
                        end = time.time()
                        if end-start >= 30: # if go beyond 30 second to touch the screen -> 
                            print("Mouse didn't touch stim --> canceled trial")
                            count = 0 # count is kept at zero (then mouse has to make 5 consecutive success)
                            Success = 0 # no success
                            Touched = 0
                            init_to_touch = np.nan
                            touch_to_reward = np.nan
                            screen.fill(0) # black screen
                            pygame.display.flip()
                            timeout = True
                        else:
                            for e in pygame.event.get():
                                if e.type == pygame.FINGERDOWN:
                                    coordTouch = dict((k,e.dict[k]) for k in ['x', 'y'] if k in e.dict) #register touch coordinates
                                    xy = list(coordTouch.values()) # il faut extraire coordonnées du toucher pour savoir quel stim visuel choisi
                                    
                                    if xy[0] <= blink_size[0]/screen_size[0] or xy[0] >= (screen_size[0]-blink_size[0])/screen_size[0]: # if mouse touche the screen correctly (on stim), 
                                        print("Mouse touched one white stim")
                                        startbis = time.time() # start second timer 
                                        Touched = 1
                                        init_to_touch = end - start
                                        myModules.set_doors_open()
                                        while timeout == False:
                                            end = time.time() # mouse did touch the screen: end of timer
                                            screen.blit(white, (0, screen_size[1]-blink_size[1])) 
                                            screen.blit(white, (screen_size[0]-blink_size[0], screen_size[1]-blink_size[1])) 
                                            pygame.display.flip() #show both white squares
                                            time.sleep(0.25) 
                                            screen.fill(0)
                                            pygame.display.flip() # show black screen (to blick)
                                            time.sleep(0.25)
                                            if (JuvDoorState == 1 or ObjDoorState == 1): 
                                                if end - startbis < 15: # the mouse has 15 second to go to the interaction zone before fail
                                                    count += 1 
                                                    print("Mouse in interaction zone in good timing ")
                                                    Success = 1
                                                touch_to_reward = end-startbis # the time between mouse in the zone and mouse back to the zone (stored here in case the mouse do not go to the interactionzone)
                                                time.sleep(7) # mouse has 7 seconds of interaction
                                                pygame.event.clear()
                                                myModules.set_doors_closed()
                                                timeout = True
                                            elif end-startbis >= 15: # if the mouse took too much time (more than 15 seconds)
                                                print("Mouse failed to ge to the interaction zone, trial set to 0")
                                                pygame.event.clear()
                                                myModules.set_doors_closed()
                                                touch_to_reward = np.nan
                                                count = 0
                                                Success = 0 # no success
                                                timeout = True
                                                           
                    data = [Timestamp, Trial, Touched, Success, init_to_touch, touch_to_reward]
                    with open(Data_folder + '/stage2.csv', 'a') as file:
                        writer = csv.writer(file)
                        writer.writerow(data)
                    time.sleep(5)
                    if count == consecutive_success:
                        stage = 3
                        print("Mouse succeded the stage, switch to stage ", str(stage))
                        screen.fill(0)
                        pygame.display.flip() 
                        pygame.event.clear()
                        
                        
        ######################## STAGE 3 ######################## 
        if stage == 3:
            seed(1)
            cycles = 0
            Timestamp = 0
            Trial = 0  
            socialStimSide = []
            social = 0
            nights = 0
            stable_nights = []
            percent_social_whole_night = []
            p.social = []
            p.retrieved = []
            pre_choice_social = 0
            chosenStimSide = 0
            Init2touch = 0 
            Touch2reward = 0
            recInteractionTime = 0
            uniInteractionTime = 0
            noInteractionTime = 0
            header = ['Timestamp', 'Trial',"Prechoicesocial" , 'SocialStimSide', 'ChosenStimSide', 'SocialChosen', 'Init2touch', 'Touch2reward', 
                      'RecInteractionTime', 'UniInteractionTime', 'NoInteractionTime', 'Dark']
            with open(Data_folder + '/stage3.csv', 'w') as file:
                writer = csv.writer(file)
                writer.writerow([Start_date])
                writer.writerow('')
                writer.writerow(['Mouse ID: ', MouseID])
                writer.writerow(['DoB: ', MouseDoB])
                writer.writerow(['isKO (1 = LgDel): ', isKO])
                writer.writerow(['Stim side (1 = right): ', stimSide])   
                writer.writerow(['Visual stim leading to social stim (0 = grid & 1 = lines): ', socialRewardStim])
                writer.writerow('')
                writer.writerow(header)
            
            ######################## STAGE 3 GAME LOOP ######################## 
            while stage == 3:
                now = datetime.now()
                
                        
                if (JuvDoorState == 1 or ObjDoorState == 1):
                    if JuvDoorState == 1:
                        pre_choice_social =  1
                        print("Mouse prechoice: social, strats trial ", str(Trial+1))
                    elif ObjDoorState == 1:
                        pre_choice_social = 0
                        print("Mouse prechoice: object, strats trial ", str(Trial+1))
                    start = time.time()
                    Timestamp = start-Task_start
                    Trial += 1
                    timeout = False
                    pygame.event.clear()
                    
                    if len(socialStimSide) > 9: ### force to change if too much same iteration
                        if (sum(socialStimSide[-3:]) == 3 or sum(socialStimSide[-3:]) == 0 or 
                            sum(socialStimSide[-10:]) == 7 or sum(socialStimSide[-10:]) == 3):
                            socialStimSide.append(abs(socialStimSide[-1] - 1))
                        else:
                            socialStimSide.append(random.randint(0, 1))
                    elif len(socialStimSide) > 2:
                        if sum(socialStimSide[-3:]) == 3 or sum(socialStimSide[-3:]) == 0:
                            socialStimSide.append(abs(socialStimSide[-1] - 1))
                        else:
                            socialStimSide.append(random.randint(0, 1))
                    else:
                        socialStimSide.append(random.randint(0, 1))
                    
                    #print(socialStimSide)
    
                    if (socialStimSide[-1] == 1 and socialRewardStim == 1) or (socialStimSide[-1] == 0 and socialRewardStim == 0): 
                        screen.blit(grid, (0, screen_size[1]-grid_size[1]))
                        screen.blit(line, (screen_size[0]-line_size[0], screen_size[1]-line_size[1]))
                    elif (socialStimSide[-1] == 0 and socialRewardStim == 1) or (socialStimSide[-1] == 1 and socialRewardStim == 0):
                        screen.blit(line, (0, screen_size[1]-line_size[1]))
                        screen.blit(grid, (screen_size[0]-grid_size[0], screen_size[1]-grid_size[1]))                
                    pygame.display.flip()
                    
                    while timeout == False:
                        end = time.time()
                        if end-start >= 30: 
                            noInteractionTime = float("NaN")
                            recInteractionTime = float("NaN")
                            uniInteractionTime = float("NaN")
                            chosenStimSide = float("NaN")
                            social = float("NaN")
                            Init2touch = float("NaN")
                            Touch2reward = float("NaN")
                            pygame.event.clear()
                            data = [Timestamp, Trial, pre_choice_social, socialStimSide[-1], chosenStimSide, social, Init2touch, Touch2reward, 
                                    recInteractionTime, uniInteractionTime, noInteractionTime, dark]
                            with open(Data_folder + '/stage3.csv', 'a') as file:
                                writer = csv.writer(file)
                                writer.writerow(data)
                            noInteractionTime = 0
                            recInteractionTime = 0
                            uniInteractionTime = 0
                            timeout = True
                            screen.fill(0)
                            pygame.display.flip()
                        else:
                            for e in pygame.event.get():
                                if e.type == pygame.FINGERDOWN: 
                                    coordTouch = dict((k,e.dict[k]) for k in ['x', 'y'] if k in e.dict) 
                                    xy = list(coordTouch.values())
                                    startbis = time.time()
                                    Init2touch = end-start
                                    if (xy[0] <= blink_size[0]/screen_size[0] and socialStimSide[-1] == 0) or\
                                        (xy[0] >= (screen_size[0]-blink_size[0])/screen_size[0] and socialStimSide[-1] == 1): # If the mouse click on the social stim on screen
                                        chosenStimSide = socialStimSide[-1]
                                        social=1
                                        #print("mouse clicked on social stim")
                                        myModules.set_door_open_S()
                                        timeout = False
                                        while timeout == False:
                                            end = time.time()
                                            screen.blit(white, (0, screen_size[1]-blink_size[1]))
                                            screen.blit(white, (screen_size[0]-blink_size[0], screen_size[1]-blink_size[1]))
                                            pygame.display.flip()
                                            time.sleep(0.25)
                                            screen.fill(0)
                                            pygame.display.flip()
                                            time.sleep(0.25)
                                            if JuvDoorState == 1: 
                                                #print("Mouse is back on social side")
                                                Touch2reward = end-startbis
                                                p.retrieved.append(1)
                                                startInteraction = time.time()
                                                screen.fill(0)
                                                pygame.display.flip() # back to reward, black screen
                                                startInteracTime = 0
                                                noInterac = 0
                                                uniInterac = 0
                                                recInterac = 0
                                                startedRec = 0
                                                startedUni = 0
                                                startedNo = 0
                                                while timeout == False:
                                                    endInteraction = time.time()
                                                    if endInteraction-startInteraction >= 7:
                                                        #print("mouse interacted, now, end of interaction")
                                                        timeout = True
                                                        if noInterac:
                                                            noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                        elif uniInterac:
                                                            uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                        elif recInterac:
                                                            recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                    elif JuvDoorState and JuvDoorStimState:
                                                        recInterac = 1
                                                        if noInterac:
                                                            noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                            noInterac = 0
                                                            startedNo = 0
                                                        elif uniInterac:
                                                            uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                            uniInterac = 0
                                                            startedUni = 0
                                                        if startedRec == 0:
                                                            startInteracTime = time.time()
                                                            startedRec = 1
                                                    elif JuvDoorState and not JuvDoorStimState:
                                                        uniInterac = 1
                                                        if noInterac:
                                                            noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                            noInterac = 0
                                                            startedNo = 0
                                                        elif recInterac:
                                                            recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                            recInterac = 0
                                                            startedRec = 0
                                                        if startedUni == 0:
                                                            startInteracTime = time.time()
                                                            startedUni = 1
                                                    else:
                                                        noInterac = 1
                                                        if recInterac:
                                                            recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                            recInterac = 0
                                                            startedRec = 0
                                                        elif uniInterac:
                                                            uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                            uniInterac = 0
                                                            startedUni = 0
                                                        if startedNo == 0:
                                                            startInteracTime = time.time()
                                                            startedNo = 1
                                                            
                                                myModules.set_door_closed_S()
                                                
                                            elif end-startbis >= 10:
                                                #print("Mouse didn't went back to reward")
                                                p.retrieved.append(0)
                                                noInteractionTime = float("NaN")
                                                recInteractionTime = float("NaN")
                                                uniInteractionTime = float("NaN")
                                                Touch2reward = float("NaN")
                                                pygame.event.clear()
                                                myModules.set_door_closed_S()
                                                timeout = True
                                        data = [Timestamp, Trial, pre_choice_social, socialStimSide[-1], chosenStimSide, social, Init2touch, Touch2reward, 
                                                recInteractionTime, uniInteractionTime, noInteractionTime, dark]
                                        p.social.append(social)
                                        with open(Data_folder + '/stage3.csv', 'a') as file:
                                            writer = csv.writer(file)
                                            writer.writerow(data)
                                        noInteractionTime = 0
                                        recInteractionTime = 0
                                        uniInteractionTime = 0
                                    elif (xy[0] <= blink_size[0]/screen_size[0] and socialStimSide[-1] == 1) or\
                                        (xy[0] >= (screen_size[0]-blink_size[0])/screen_size[0] and socialStimSide[-1] == 0):
                                        chosenStimSide = abs(socialStimSide[-1]-1)
                                        social=0
                                        #print("Mouse clicked on object stim")
                                        myModules.set_door_open_NS()
                                        timeout = False
                                        while timeout == False:
                                            end = time.time()
                                            screen.blit(white, (0, screen_size[1]-blink_size[1]))
                                            screen.blit(white, (screen_size[0]-blink_size[0], screen_size[1]-blink_size[1]))
                                            pygame.display.flip()
                                            time.sleep(0.25)
                                            screen.fill(0)
                                            pygame.display.flip()
                                            time.sleep(0.25)
                                            if ObjDoorState: 
                                                #print("Mouse is back on object side")
                                                p.retrieved.append(1)
                                                screen.fill(0)
                                                pygame.display.flip() # back to reward, black screen
                                                startInteraction = time.time()
                                                startInteracTime = 0
                                                noInterac = 0
                                                uniInterac = 0
                                                recInterac = 0
                                                startedRec = 0
                                                startedUni = 0
                                                startedNo = 0
                                                Touch2reward = end-startbis
                                                while timeout == False:
                                                    endInteraction = time.time()
                                                    if endInteraction-startInteraction >= 7:
                                                        timeout = True
                                                        if noInterac:
                                                            noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                        elif uniInterac:
                                                            uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                        elif recInterac:
                                                            recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                    elif ObjDoorState and ObjDoorStimZone: #ObjDoorStimZone is not a function cause cause there is no camera on the object stim side
                                                        recInterac = 1
                                                        if noInterac:
                                                            noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                            noInterac = 0
                                                            startedNo = 0
                                                        elif uniInterac:
                                                            uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                            uniInterac = 0
                                                            startedUni = 0
                                                        if startedRec == 0:
                                                            startInteracTime = time.time()
                                                            startedRec = 1
                                                    elif ObjDoorState and not ObjDoorStimZone:
                                                        uniInterac = 1
                                                        if noInterac:
                                                            noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                            noInterac = 0
                                                            startedNo = 0
                                                        elif recInterac:
                                                            recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                            recInterac = 0
                                                            startedRec = 0
                                                        if startedUni == 0:
                                                            startInteracTime = time.time()
                                                            startedUni = 1
                                                    else:
                                                        noInterac = 1
                                                        if recInterac:
                                                            recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                            recInterac = 0
                                                            startedRec = 0
                                                        elif uniInterac:
                                                            uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                            uniInterac = 0
                                                            startedUni = 0
                                                        if startedNo == 0:
                                                            startInteracTime = time.time()
                                                            startedNo = 1 
                                                pygame.event.clear()
                                                myModules.set_door_close_NS()
                                            elif end-startbis >= 10:
                                                p.retrieved.append(0)
                                                noInteractionTime = float("NaN")
                                                recInteractionTime = float("NaN")
                                                uniInteractionTime = float("NaN")
                                                Touch2reward = float("NaN")
                                                pygame.event.clear() # avoid lunching multiple trials by multiple press
                                                myModules.set_door_close_NS()
                                                timeout = True
                                        data = [Timestamp, Trial, pre_choice_social, socialStimSide[-1], chosenStimSide, social, Init2touch, Touch2reward, 
                                                recInteractionTime, uniInteractionTime, noInteractionTime, dark]
                                        p.social.append(social)
                                        with open(Data_folder + '/stage3.csv', 'a') as file:
                                            writer = csv.writer(file)
                                            writer.writerow(data)
                                        noInteractionTime = 0
                                        recInteractionTime = 0
                                        uniInteractionTime = 0
                time.sleep(5)
                pygame.event.clear()
                # if p.retrieved[-3:] == [1, 1, 1]: # à changer tout ça !! track stabilité choix souris
                #     stage = 4 # In this stage, the effort component will be implemented
                #     print("mouse succeded the stage, switch to stage ", str(stage))
                #     screen.fill(0)
                #     pygame.display.flip()
                #     pygame.event.clear()
                #   
                
                if now.hour >= 8  and now.hour < 20:
                    if dark == 1:
                        dark = 0
                        p.social = []
                        p.retrieved = [] # the perfs are reset to 0 at the begining of the night
                        
                else:
                    if dark == 0:   
                        dark = 1 # If there is a switch from dark to light...
                        nights += 1
                        ####### intra-session stability ###########
                        # create "stop points" where the mice has retrieved 40 time in a row the reward (social or non social)
                        temp_list = [] 
                        success_stop_points_ret = []
                        success_stop_points_soc = []
                        
                        
                        for i in p.retrieved:
                            temp_list.append(i) # checks the retrieved list in an iterative manner
                            if sum(temp_list[-40:]) == 40: # all last 40 retrieved were equal to 1
                                last_point_soc = sum(temp_list) # We take the sum as index because we take only success retrieved (which has a corresponding social value)
                                last_point_ret = len(temp_list) # len of temp list to keep track of number of trials 
                                if len(success_stop_points_ret) >= 1:
                                    if last_point_ret > success_stop_points_ret[-1]+40: # We check if this new stop point (last point), is at least superior by 40 to the last success stop point.
                                        success_stop_points_soc.append(last_point_soc)
                                        success_stop_points_ret.append(last_point_ret)
                                else:
                                    success_stop_points_soc.append(last_point_soc)
                                    success_stop_points_ret.append(last_point_ret)
                                    
                                    
                        # check performance at beginning middle and end of the night
                        if len(success_stop_points_soc) >= 3: # The mouse has to make at least three time 40 consecutive retrived (minimum 120 trial)
                            percent_social = []
                            for j in success_stop_points_soc:
                                percent_social.append(sum(p.social[j-40:j])/40)
                            percent_social_comp = [percent_social[0], findMiddle(percent_social), percent_social[-1]]
                            success_stop_points_comp = [success_stop_points_soc[0], findMiddle(success_stop_points_soc), success_stop_points_soc[-1]]
                            # check if performance at beginning middle and end of the night are similar
                            inside_tunnel_intra = []
                            #mediane_percent_social  = np.median(percent_social_comp)
                            for i in percent_social_comp[1:]:
                                if percent_social_comp[0] - 0.1 <= i <= percent_social_comp[0] + 0.1:
                                    inside_tunnel_intra.append(1)
                                else:
                                    inside_tunnel_intra.append(0)
                            if inside_tunnel_intra == [1,1]: # check if social performance is constant at the three night timepoints
                                stable_nights.append(1)
                                percent_social_whole_night.append(sum(p.social)/len(p.social))
                                print("SUCCEED! Performance of the night: \n Purcent social choice: ",percent_social_comp)
                                p.social = []
                                p.retrieved = []
                            else:
                                stable_nights.append(0)
                                print("FAILED! Performance of the night: \n Purcent social choice: ",percent_social_comp)
                                p.social = []
                                p.retrieved = []
                            ####### inter-session stability ###########
                            if len(stable_nights) >= 3:
                                if stable_nights[-3:] == [1,1,1]:
                                    inside_tunnel_inter = [] 
                                    for i in percent_social_whole_night[-2:]:
                                        if percent_social_whole_night[-3] - 0.1 <= i <= percent_social_whole_night[-3] + 0.1:
                                            inside_tunnel_inter.append(1)
                                        else:
                                            inside_tunnel_inter.append(0)
                                    if  inside_tunnel_inter == [1,1]:# the first night (three nights ago) is the reference point (stable)
                                        print("Mouse succeded the stage, switch to stage 4 \n Performances whole nights ", percent_social_whole_night[-3:])
                                        stage = 4
                                    else:
                                        print("NOT 3 CONSECUTIVE STABLE NIGHTS (",percent_social_whole_night[-3],"), START FROM 0: \n night stability:", percent_social_whole_night[-3:])
                        else:
                            print("FAILED: not enought success retrieved!")
                            stable_nights.append(0)
                            p.social = []
                            p.retrieved = []
                            
        ######################## STAGE 4 ########################            
        if stage == 4:
            seed(1)
            cycles = 0
            now = datetime.now()
            Timestamp = 0
            Trial = 0  
            socialStimSide = []
            social = 0
            nights = 0 
            stable_nights = []
            percent_social_whole_night = []
            p.social = []
            p.retrieved = []
            pre_choice_social = 0
            pre_choice_object = 0
            chosenStimSide = 0
            Init2touch = 0 
            Touch2reward = 0
            recInteractionTime = 0
            uniInteractionTime = 0
            noInteractionTime = 0
            count_s_touch = 0
            count_ns_touch = 0
            last_three_social_efforts = []
            last_three_object_effort = []
            last_ten_social_efforts = []
            last_ten_effort_options = []
            effort_iteration = []
            effort_level = []
            last_three_elements = []
            last_ten_elements = []
    
            
            
            
            header = ['Timestamp', 'Trial',"Effortlevel_S","Effortlevel_NS", "Prechoicesocial", 'SocialStimSide', 'ChosenStimSide', 'SocialChosen', 'Init2touch', 'Touch2reward', 
                      'RecInteractionTime', 'UniInteractionTime', 'NoInteractionTime', 'Dark']
            with open(Data_folder + '/stage4.csv', 'w') as file:
                writer = csv.writer(file)
                writer.writerow([Start_date])
                writer.writerow('')
                writer.writerow(['Mouse ID: ', MouseID])
                writer.writerow(['DoB: ', MouseDoB])
                writer.writerow(['isKO (1 = LgDel): ', isKO])
                writer.writerow(['Stim side (1 = right): ', stimSide])   
                writer.writerow(['Visual stim leading to social stim (0 = grid & 1 = lines): ', socialRewardStim])
                writer.writerow('')
                writer.writerow(header)
            
            ######################## STAGE 4 GAME LOOP ######################## 
            while stage == 4:
                time.sleep(0.05)
                if (JuvDoorState == 1 or ObjDoorState == 1):
                    if JuvDoorState == 1:
                        pre_choice_social =  1
                        print("Mouse prechoice: social, starts trial ")
                    elif ObjDoorState == 1:
                        pre_choice_social = 0
                        print("Mouse prechoice: object, starts trial ")
                    start = time.time()
                    Timestamp = start-Task_start
                    Trial += 1
                    timeout = False
                    
                    # Randomation control for social stim side
                    if len(socialStimSide) > 9: ### force to change if too much same iteration
                        if (sum(socialStimSide[-3:]) == 3 or sum(socialStimSide[-3:]) == 0 or 
                            sum(socialStimSide[-10:]) == 7 or sum(socialStimSide[-10:]) == 3):
                            socialStimSide.append(abs(socialStimSide[-1] - 1))
                        else:
                            socialStimSide.append(random.randint(0, 1))
                    elif len(socialStimSide) > 2:
                        if sum(socialStimSide[-3:]) == 3 or sum(socialStimSide[-3:]) == 0:
                            socialStimSide.append(abs(socialStimSide[-1] - 1))
                        else:
                            socialStimSide.append(random.randint(0, 1))
                    else:
                        socialStimSide.append(random.randint(0, 1))
                        
                    print(socialStimSide)
                    
                    # randomization control for effort level
                    effort_iteration = random.sample(range(0, 4), 2)
                    last_three_social_efforts = [e[0] for e in last_three_elements] # for social stim
                    last_three_object_effort = [e[1] for e in last_three_elements] # for object stim
                    last_ten_social_efforts = [e[0] for e in last_ten_elements]
                    last_ten_object_effort = [e[1] for e in last_ten_elements]
                    
                    if len(effort_level) > 2:
                        if last_three_social_efforts == [0, 0, 0]:
                            effort_iteration[0] = random.choice(range(1, 4))
                        elif last_three_social_efforts == [1, 1, 1]:
                            effort_iteration[0] = random.choice([0, 2, 3])
                        elif last_three_social_efforts == [2, 2, 2]:
                            effort_iteration[0] = random.choice([0, 1, 3])
                        elif last_three_social_efforts == [3, 3, 3]:
                            effort_iteration[0] = random.choice(range(0, 3))
                
                        if last_three_object_effort == [0, 0, 0]:
                            effort_iteration[1] = random.choice(range(1, 4))
                        elif last_three_object_effort == [1, 1, 1]:
                            effort_iteration[1] = random.choice([0, 2, 3])
                        elif last_three_object_effort == [2, 2, 2]:
                            effort_iteration[1] = random.choice([0, 1, 3])
                        elif last_three_object_effort == [3, 3, 3]:
                            effort_iteration[1] = random.choice(range(0, 3))
                
                    elif len(effort_level) > 9:
                        if last_ten_social_efforts.count(0) > 6:
                            effort_iteration[0] = random.choice(range(1, 4))
                        elif last_ten_social_efforts.count(1) > 6:
                            effort_iteration[0] = random.choice([0, 2, 3])
                        elif last_ten_social_efforts.count(2) > 6:
                            effort_iteration[0] = random.choice([0, 1, 3])
                        elif last_ten_social_efforts.count(3) > 6:
                            effort_iteration[0] = random.choice(range(0, 3))
                
                        if last_ten_effort_options.count(0) > 6:
                            effort_iteration[1] = random.choice(range(1, 4))
                        elif last_ten_effort_options.count(1) > 6:
                            effort_iteration[1] = random.choice([0, 2, 3])
                        elif last_ten_effort_options.count(2) > 6:
                            effort_iteration[1] = random.choice([0, 1, 3])
                        elif last_ten_effort_options.count(3) > 6:
                            effort_iteration[1] = random.choice(range(0, 3))
                
                    effort_level.append(effort_iteration)
                    last_three_elements = effort_level[-3:]
                    last_ten_elements = effort_level[-10:]
                    
                    print(effort_level)
                    print("effort social: ", effort_level[-1][0], "effort non-social: ", effort_level[-1][1])
                   
                    if (socialStimSide[-1] == 1 and socialRewardStim == 1) or (socialStimSide[-1] == 0 and socialRewardStim == 0): #socialRewardStim is attributed to lines (1) or to grid (0)
                        screen.blit(grid, (margin, screen_size[1]-grid_size[1]))
                        screen.blit(line, (screen_size[0]-line_size[0]-margin, screen_size[1]-line_size[1]))
                        
                    elif (socialStimSide[-1] == 0 and socialRewardStim == 1) or (socialStimSide[-1] == 1 and socialRewardStim == 0):
                        screen.blit(line, (margin, screen_size[1]-line_size[1]))
                        screen.blit(grid, (screen_size[0]-grid_size[0]-margin, screen_size[1]-grid_size[1]))  
                        
                    # Social effort levels:
                        # (left side)
                    if socialStimSide[-1] == 0: # socialstimside == 1 means on the right/ == 0 means on the left
                        if effort_level[-1][0] == 1: 
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]/6), 60)    # first dot on left
                        elif effort_level[-1][0] == 2:
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]/6), 60)
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]/2), 60)
                        elif effort_level[-1][0] == 3:
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]/6), 60)
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]/2), 60)
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]*5/6), 60)
                        # (right side)
                    else:
                        if effort_level[-1][0] == 1:
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]/6), 60)
                        elif effort_level[-1][0] == 2:
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]/6), 60)
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]/2), 60)
                        elif effort_level[-1][0] == 3:
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]/6), 60)
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]/2), 60)
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]*5/6), 60)
                    
                    
                    # Non social effort levels:
                        #circles are drawn on the other side of the screen (oposite to the social stim side)
                        #(right)
                    if socialStimSide[-1] == 0:
                        if effort_level[-1][1] == 1:
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]/6), 60)
                        elif effort_level[-1][1] == 2: 
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]/6), 60)
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]/2), 60)
                        elif effort_level[-1][1] == 3:
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]/6), 60)
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]/2), 60)
                            pygame.draw.circle(screen, (255,255,255), (screen_size[0]-margin/2, screen.get_height()-grid_size[1]*5/6), 60)
                    
                    else:
                        if effort_level[-1][1] == 1:
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]/6), 60)
                        elif effort_level[-1][1] == 2: 
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]/6), 60)
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]/2), 60)
                        elif effort_level[-1][1] == 3:
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]/6), 60)
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]/2), 60)
                            pygame.draw.circle(screen, (255,255,255), (margin/2, screen.get_height()-grid_size[1]*5/6), 60)
                   
                    
                    pygame.display.flip()
                    
                    while timeout == False:
                        end = time.time()
                        if end-start >= 10: # devrait être 30
                            noInteractionTime = float("NaN")
                            recInteractionTime = float("NaN")
                            uniInteractionTime = float("NaN")
                            chosenStimSide = float("NaN")
                            social = float("NaN")
                            Init2touch = float("NaN")
                            Touch2reward = float("NaN")
                            pygame.event.clear()
                            data = [Timestamp, Trial, effort_level[-1][0], effort_level[-1][1], pre_choice_social, socialStimSide[-1], chosenStimSide, social, Init2touch, Touch2reward, 
                                    recInteractionTime, uniInteractionTime, noInteractionTime, dark]
                            with open(Data_folder + '/stage4.csv', 'a') as file:
                                writer = csv.writer(file)
                                writer.writerow(data)
                            noInteractionTime = 0
                            recInteractionTime = 0
                            uniInteractionTime = 0
                            timeout = True
                            screen.fill(0)
                            pygame.display.flip()
                            
                        else:
                            for e in pygame.event.get():
                                if e.type == pygame.FINGERDOWN: 
                                    coordTouch = dict((k,e.dict[k]) for k in ['x', 'y'] if k in e.dict) 
                                    xy = list(coordTouch.values()) 
                                    startbis = time.time()
                                    Init2touch = end-start
                                    if (margin/screen_size[0] <= xy[0] <= (blink_size[0]+margin)/screen_size[0] and socialStimSide[-1] == 0) or\
                                        ((screen_size[0]-margin)/screen_size[0]>=xy[0] >= (screen_size[0]-margin-blink_size[0])/screen_size[0] and socialStimSide[-1] == 1): # If the mouse click on the social stim on screen
                                        chosenStimSide = socialStimSide[-1]
                                        count_s_touch += 1
                                        print("mouse clicked on social stim ", count_s_touch, "time(s)")
                                        if count_s_touch >= effort_level[-1][0]*3 or effort_level[-1][0] == 0:
                                            social=1
                                            p.social.append(social)
                                            myModules.set_door_open_S()
                                            # effort_iteration = random.sample(range(0, 4), 2)
                                            count_s_touch = 0
                                            timeout = False
                                            while timeout == False:
                                                end = time.time()
                                                screen.blit(white, (margin, screen_size[1]-blink_size[1]))
                                                screen.blit(white, (screen_size[0]-blink_size[0]-margin, screen_size[1]-blink_size[1]))
                                                pygame.display.flip()
                                                time.sleep(0.25)
                                                screen.fill(0)
                                                pygame.display.flip()
                                                time.sleep(0.25)
                                                if JuvDoorState: 
                                                    print("mouse is back on social side")
                                                    p.retrieved.append(1)
                                                    startInteraction = time.time()
                                                    startInteracTime = 0
                                                    noInterac = 0
                                                    uniInterac = 0
                                                    recInterac = 0
                                                    startedRec = 0
                                                    startedUni = 0
                                                    startedNo = 0
                                                    Touch2reward = end-startbis
                                                    while timeout == False:
                                                        endInteraction = time.time()
                                                        if endInteraction-startInteraction >= 7:
                                                            timeout = True
                                                            if noInterac:
                                                                noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                            elif uniInterac:
                                                                uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                            elif recInterac:
                                                                recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                        elif JuvDoorState and JuvDoorStimState: 
                                                            recInterac = 1
                                                            if noInterac:
                                                                noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                                noInterac = 0
                                                                startedNo = 0
                                                            elif uniInterac:
                                                                uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                                uniInterac = 0
                                                                startedUni = 0
                                                            if startedRec == 0:
                                                                startInteracTime = time.time()
                                                                startedRec = 1
                                                        elif JuvDoorState and not JuvDoorStimState:
                                                            uniInterac = 1
                                                            if noInterac:
                                                                noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                                noInterac = 0
                                                                startedNo = 0
                                                            elif recInterac:
                                                                recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                                recInterac = 0
                                                                startedRec = 0
                                                            if startedUni == 0:
                                                                startInteracTime = time.time()
                                                                startedUni = 1
                                                        else:
                                                            noInterac = 1
                                                            if recInterac:
                                                                recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                                recInterac = 0
                                                                startedRec = 0
                                                            elif uniInterac:
                                                                uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                                uniInterac = 0
                                                                startedUni = 0
                                                            if startedNo == 0:
                                                                startInteracTime = time.time()
                                                                startedNo = 1
                                                    
                                                    myModules.set_door_closed_S()
                                                elif end-startbis >= 10:
                                                    p.retrieved.append(0)
                                                    noInteractionTime = float("NaN")
                                                    recInteractionTime = float("NaN")
                                                    uniInteractionTime = float("NaN")
                                                    Touch2reward = float("NaN")
                                                    myModules.set_door_closed_S()
                                                    pygame.event.clear()
                                                    timeout = True
                                        
                                        if timeout == True:
                                            data = [Timestamp, Trial, effort_level[-1][0], effort_level[-1][1], pre_choice_social, socialStimSide[-1], chosenStimSide, social, Init2touch, Touch2reward, 
                                                    recInteractionTime, uniInteractionTime, noInteractionTime, dark]
                                            with open(Data_folder + '/stage4.csv', 'a') as file:
                                                writer = csv.writer(file)
                                                writer.writerow(data)
                                            noInteractionTime = 0
                                            recInteractionTime = 0
                                            uniInteractionTime = 0
                                    elif (margin/screen_size[0] <= xy[0] <= (blink_size[0]+margin)/screen_size[0] and socialStimSide[-1] == 1) or\
                                        ((screen_size[0]-margin)/screen_size[0]>=xy[0] >= (screen_size[0]-margin-blink_size[0])/screen_size[0] and socialStimSide[-1] == 0):
                                        chosenStimSide = abs(socialStimSide[-1]-1)
                                        count_ns_touch += 1
                                        print("mouse clicked on non-social stim ", count_ns_touch, "time(s)")
                                        if count_ns_touch >= effort_level[-1][1]*3 or effort_level[-1][1] == 0:
                                            social=0
                                            p.social.append(social)
                                            myModules.set_door_open_NS()
                                            count_ns_touch = 0
                                            timeout = False
                                            while timeout == False:
                                                end = time.time()
                                                screen.blit(white, (margin, screen_size[1]-blink_size[1]))
                                                screen.blit(white, (screen_size[0]-blink_size[0]-margin, screen_size[1]-blink_size[1]))
                                                pygame.display.flip()
                                                time.sleep(0.25)
                                                screen.fill(0)
                                                pygame.display.flip()
                                                time.sleep(0.25)
                                                if ObjDoorState: 
                                                    print("Mouse is back on object side")
                                                    p.retrieved.append(1)
                                                    startInteraction = time.time()
                                                    startInteracTime = 0
                                                    noInterac = 0
                                                    uniInterac = 0
                                                    recInterac = 0
                                                    startedRec = 0
                                                    startedUni = 0
                                                    startedNo = 0
                                                    Touch2reward = end-startbis
                                                    while timeout == False:
                                                        endInteraction = time.time()
                                                        if endInteraction-startInteraction >= 7:
                                                            timeout = True
                                                            if noInterac:
                                                                noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                            elif uniInterac:
                                                                uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                            elif recInterac:
                                                                recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                        elif ObjDoorState and ObjDoorStimZone: #ObjDoorStimZone is not a function cause cause there is no camera on the object stim side
                                                            recInterac = 1
                                                            if noInterac:
                                                                noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                                noInterac = 0
                                                                startedNo = 0
                                                            elif uniInterac:
                                                                uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                                uniInterac = 0
                                                                startedUni = 0
                                                            if startedRec == 0:
                                                                startInteracTime = time.time()
                                                                startedRec = 1
                                                        elif ObjDoorState and not ObjDoorStimZone:
                                                            uniInterac = 1
                                                            if noInterac:
                                                                noInteractionTime = noInteractionTime+(endInteraction-startInteracTime)
                                                                noInterac = 0
                                                                startedNo = 0
                                                            elif recInterac:
                                                                recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                                recInterac = 0
                                                                startedRec = 0
                                                            if startedUni == 0:
                                                                startInteracTime = time.time()
                                                                startedUni = 1
                                                        else:
                                                            noInterac = 1
                                                            if recInterac:
                                                                recInteractionTime = recInteractionTime+(endInteraction-startInteracTime)
                                                                recInterac = 0
                                                                startedRec = 0
                                                            elif uniInterac:
                                                                uniInteractionTime = uniInteractionTime+(endInteraction-startInteracTime)
                                                                uniInterac = 0
                                                                startedUni = 0
                                                            if startedNo == 0:
                                                                startInteracTime = time.time()
                                                                startedNo = 1 
                                                    myModules.set_door_close_NS()
                                                    pygame.event.clear()
                                                elif end-startbis >= 10:
                                                    p.retrieved.append(0)
                                                    noInteractionTime = float("NaN")
                                                    recInteractionTime = float("NaN")
                                                    uniInteractionTime = float("NaN")
                                                    Touch2reward = float("NaN")
                                                    myModules.set_door_close_NS()
                                                    pygame.event.clear()
                                                    
                                                    timeout = True
                                        if timeout == True:
                                            data = [Timestamp, Trial, effort_level[-1][0], effort_level[-1][1], pre_choice_social, socialStimSide[-1], chosenStimSide, social, Init2touch, Touch2reward, 
                                                    recInteractionTime, uniInteractionTime, noInteractionTime, dark]
                                            with open(Data_folder + '/stage4.csv', 'a') as file:
                                                writer = csv.writer(file)
                                                writer.writerow(data)
                                            noInteractionTime = 0
                                            recInteractionTime = 0
                                            uniInteractionTime = 0
                time.sleep(5)
                pygame.event.clear()
                # if p.retrieved[-3:] == [1, 1, 1]: # à changer tout ça !! stabilité choix souris
                #     stage = 5 
                #     print("mouse succeded the stage, end of experiment")
                #     screen.fill(0)
                #     pygame.display.flip()
                #     pygame.event.clear()
                #     going = False
                if now.hour >= 8  and now.hour < 20:
                    if dark == 1:
                        dark = 0
                        p.social = []
                        p.retrieved = [] # the perfs are reset to 0 at the begining of the night
                            
                else:
                    if dark == 0:
                        dark = 1 # If there is a switch from dark to light...
                        nights += 1
                        ####### intra-session stability ###########
                        # create "stop points" where the mice has retrieved 40 time in a row the reward (social or non social)
                        temp_list = [] 
                        success_stop_points_ret = []
                        success_stop_points_soc = []
                        for i in p.retrieved:
                            temp_list.append(i) # checks the retrieved list in an iterative manner
                            if sum(temp_list[-40:]) == 40: # all last 40 retrieved were equal to 1
                                last_point_soc = sum(temp_list) # We take th sum as index because we take only success retrieved (which has a corresponding social value)
                                last_point_ret = len(temp_list) # len of temp list to keep track of number of trials 
                                if len(success_stop_points_ret) >= 1:
                                    if last_point_ret > success_stop_points_ret[-1]+40: # We check if this new stop point (last point), is at least superior by 40 to the last success stop point.
                                        success_stop_points_soc.append(last_point_soc)
                                        success_stop_points_ret.append(last_point_ret)
                                else:
                                    success_stop_points_soc.append(last_point_soc)
                                    success_stop_points_ret.append(last_point_ret)
                        # check performance at beginning middle and end of the night
                        if len(success_stop_points_soc) >= 3: # The mouse has to make at least three time 40 consecutive retrived (minimum 120 trial)
                            percent_social = []
                            for j in success_stop_points_soc:
                                percent_social.append(sum(p.social[j-40:j])/40)
                            percent_social_comp = [percent_social[0], findMiddle(percent_social), percent_social[-1]]
                            success_stop_points_comp = [success_stop_points_soc[0], findMiddle(success_stop_points_soc), success_stop_points_soc[-1]]
                            # check if performance at beginning middle and end of the night are similar
                            inside_tunnel_intra = []
                            #mediane_percent_social  = np.median(percent_social_comp)
                            for i in percent_social_comp[1:]:
                                if percent_social_comp[0] - 0.1 <= i <= percent_social_comp[0] + 0.1:
                                    inside_tunnel_intra.append(1)
                                else:
                                    inside_tunnel_intra.append(0)
                            if inside_tunnel_intra == [1,1]: # check if social performance is constant at the three night timepoints
                                stable_nights.append(1)
                                percent_social_whole_night.append(sum(p.social)/len(p.social))
                                print("SUCCEED! Performance of the night: \n Purcent social choice: ",percent_social_comp)
                                p.social = []
                                p.retrieved = []
                            else:
                                stable_nights.append(0)
                                print("FAILED! Performance of the night: \n Purcent social choice: ",percent_social_comp)
                                p.social = []
                                p.retrieved = []
                            ####### inter-session stability ###########
                            if len(stable_nights) >= 3:
                                if stable_nights[-3:] == [1,1,1]:
                                    inside_tunnel_inter = [] 
                                    for i in percent_social_whole_night[-2:]:
                                        if percent_social_whole_night[-3] - 0.1 <= i <= percent_social_whole_night[-3] + 0.1:
                                            inside_tunnel_inter.append(1)
                                        else:
                                            inside_tunnel_inter.append(0)
                                    if  inside_tunnel_inter == [1,1]:# the first night (three nights ago) is the reference point (stable)
                                        print("Mouse succeded the stage, end of experiment \n Performances whole nights ", percent_social_whole_night[-3:])
                                        going = False
                                    else:
                                        print("NOT 3 CONSECUTIVE STABLE NIGHTS (",percent_social_whole_night[-3],"), START FROM 0: \n night stability:", percent_social_whole_night[-3:])
                        else:
                            print("FAILED: not enought success retrieved!")
                            stable_nights.append(0)
                            p.social = []
                            p.retrieved = []
                
        else:
            going = False
            
        pygame.display.update()

except KeyboardInterrupt:
    time.sleep(1)
    myModules.reset_flag()
    time.sleep(1)
    myModules.stop()
    time.sleep(0.1)
    pygame.quit()
    print("end of experiment")
    
# weight1.startTare(1) # poids de la souris
# weight1.startTare(0) # poids de la bouteille

# weight1.startWeightMeasure(1) # à corriger...
# weight1.startWeightMeasure(0) # no need for bottle

# weight1.getWeight(1)
# weight1.getWeight(0)

