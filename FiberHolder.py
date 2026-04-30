import numpy as np
import pyfirmata
import time

from pyfirmata import Arduino, SERVO

class FiberHolder:
    '''
    This is a wrapper for controlling a motorized, rotatable fiber holder
    controlled via a micro servo.
    '''

    def __init__(self, board, pin, orientation="counterclockwise", rotation_factor=1.0888888888888888):

        #Define arduino control board
        self.board = board

        #Define digital pin for rotation
        self.pin = pin

        #Set digital pin to SERVO
        self.board.digital[self.pin].mode = SERVO

        #Orientation of rotation
        self.orientation = orientation

        #Current angle
        self.current_angle = 0

        #Rotation factor
        self.rotation_factor = rotation_factor

        #Rotation speed
        self.rotation_speed = "FAST"

        if self.orientation == "clockwise":
            self.board.digital[self.pin].write(180*self.rotation_factor)
            # self.board.digital[self.pin].write(180)

            self.current_angle = 180*self.rotation_factor
            

    def rotate(self, angle):
        '''
        Rotates the servo (in degrees).
        '''
        if self.rotation_speed == "FAST":

            #Set digital pin to SERVO
            if self.orientation=="counterclockwise":
                self.board.digital[self.pin].write(angle*self.rotation_factor)
            else:
                self.board.digital[self.pin].write((180-(angle*self.rotation_factor)))
        else:
            rotation_delays = {
                "MEDIUM": .01,
                "SLOW": .1
            }
            angle_range = abs(int(self.current_angle - angle))
            if self.orientation == "counterclockwise":
                for i in range(angle_range+1):
                    if angle < self.current_angle:
                        self.board.digital[self.pin].write((self.current_angle - i)*self.rotation_factor)
                        time.sleep(rotation_delays[self.rotation_speed])
                    else:
                        self.board.digital[self.pin].write((self.current_angle + i)*self.rotation_factor)
                        time.sleep(rotation_delays[self.rotation_speed])
            else:
                for i in range(angle_range+1):
                    if angle < self.current_angle:
                        self.board.digital[self.pin].write((180-((self.current_angle - i))*self.rotation_factor))
                        time.sleep(rotation_delays[self.rotation_speed])
                    else:
                        self.board.digital[self.pin].write((180-((self.current_angle + i))*self.rotation_factor))
                        time.sleep(rotation_delays[self.rotation_speed])
        
        self.current_angle = angle
