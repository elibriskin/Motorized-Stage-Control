import numpy as np
import pyfirmata
import time

from pyfirmata import Arduino


class Actuator:
    '''
    This is a wrapper for controlling a 12V, 30mm linear actuator via an Arduino board,
    '''

    def __init__(self, board, in1, in2):

        #Define Arduino control board
        self.board = board

        #Define input pins for polarity control
        self.in1 = in1
        self.in2 = in2

        #Total time to extend to full stroke length in seconds
        self.total_time = 1.4

        #Total stroke length in mm
        self.total_distance=30

        self.reference = 0

    def set_reference(self):
        '''
        Sets the reference on the actuator
        '''
        self.reference = 0

    def increment_reference(self, increment):
        '''
        Increments the stored distance of the actuator
        '''
        self.reference += increment

        if self.reference > 30:
            self.reference = 30
        
        if self.reference < 0:
            self.reference = 0

    def stop(self):
        '''
        Stops the actuator
        '''
        self.board.digital[self.in1].write(0)
        self.board.digital[self.in2].write(0)

    def extend(self, distance):
        '''
        Extends the actuator forward a given distance.
        '''
        #Converts distance to corresponding HIGH duration
        duration = np.abs((self.total_time/self.total_distance)*distance)
        
        #Write to control pins
        self.board.digital[self.in1].write(1)
        self.board.digital[self.in2].write(0)
        time.sleep(duration)

        #Stop the actuator
        self.stop()

    def retract(self, distance):
        '''
        Retracts the actuator backward a given distance
        '''
        #Converts distance to corresponding HIGH duration
        duration = np.abs((self.total_time/self.total_distance)*distance)
        #Write to control pins
        self.board.digital[self.in1].write(0)
        self.board.digital[self.in2].write(1)
        time.sleep(duration)

        #Stop the actuator
        self.stop()

    def move(self, distance):
        '''
        General purpose move method for the actuator.
        '''
        if distance > 0:
            self.extend(distance)
        else:
            self.retract(distance)
        
        self.increment_reference(distance)
        
    def reset(self):
        '''
        Resets the actuator
        '''
        self.retract(-35)
        self.reference = 0


