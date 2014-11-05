# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import decimal

# Some helpers to convert timecodes to frames, back and forth
def frame_from_timecode(timecode, fps=24):
    """
    Return the frame number for the given timecode at the given fps

    :param timecode: A timecode, either 
        as a string in hour:minute:second:frame format
        or as a (hours, minutes, seconds, frames) tuple
    :param fps : Number of frames per second
    :return: Corresponding frame number, as an int
    """
    if isinstance(timecode, str) :
        (hour, minute, second, frame) = timecode.split(":")
    else: # Assume a 4 elements tuple
        (hour, minute, second, frame) = timecode
    hours = int(hour)
    minutes = int(minute)
    seconds = int(second)
    frames = int(frame)

    seconds = (hours * 60 * 60) + (minutes * 60) + seconds
    frames = (seconds * fps) + frames
    return int(round(frames))

def timecode_from_frame(frame, fps=24):
    """
    Return the timecode corresponding to the given frame, for the given fps

    :param frame: A frame number, as an int
    :param fps: Number of frames per seconds, as an int
    :return: A string in hour:minute:second:frame format
    """
    # total number of seconds in whole clip
    seconds = decimal.Decimal(frame) / fps
    # remainder frames from seconds calculation
    remainder = seconds - decimal.Decimal(int(seconds))
    frames = int(round(remainder * fps))
    # total number of minutes in the whole clip
    minutes = decimal.Decimal(int(seconds)) / 60
    # remainder seconds from minutes calculation
    remainder = minutes - decimal.Decimal(int(minutes))
    seconds = int(round(remainder * 60))
    # total number of hours in the whole clip
    hours = decimal.Decimal(int(minutes)) / 60
    # remainder minutes from hours calculation
    remainder = hours - decimal.Decimal(int(hours))
    minutes = int(round(remainder * 60))
    # hours without the remainder
    hours = int(hours)
    # Build the timecode string
    timecode = "%02d:%02d:%02d:%02d" % (hours, minutes, seconds, frames)
    return timecode

class Timecode(object):
    def __init__(self, timecode_string, fps=24):
        """
        Instantiate a timecode from a timecode string
        
        :param timecode_string: A timecode string in hour:minute:second:frame format
        """
        fields = timecode_string.split(":")
        if len(fields) != 4:
            raise ValueError(
                "Given timecode %s is not in hour:minute:second:frame format" % timecode_string
            )
        self._fps = fps
        self._hours = int(fields[0])
        self._minutes = int(fields[1])
        self._seconds = int(fields[2])
        self._frames = int(fields[3])
        # Do some basic checks
        if self._frames >= self._fps:
            raise ValueError(
                "Invalid frame value %d, it must be smaller than the framerate %d" % (
                self._frames, self._fps)
            )
        if self._hours > 23:
            raise ValueError(
                "Invalid hours value %d, it must be smaller than 24" % self._hours
            )
        if self._minutes > 59:
            raise ValueError(
                "Invalid minutes value %d, it must be smaller than 60" % self._minutes
            )
        if self._seconds > 59:
            raise ValueError(
                "Invalid seconds value %d, it must be smaller than 60" % self._seconds
            )

    @classmethod
    def from_frame(cls, frame, fps=24):
        """
        Return a new Timecode for the given frame, at the given fps
        
        :param frame: A frame number, as an int
        :param fps: Number of frames per second, as an int
        :return: A Timecode instance
        """
        return Timecode(timecode_from_frame(frame, fps), fps=fps)

    def to_frame(self):
        """
        Return the frame number corresponding to this Timecode at the given fps
        
        :return: A frame number, as an int
        """
        return frame_from_timecode(
            (self._hours, self._minutes, self._seconds, self._frames),self._fps
        )

    # Redefine some standars operators
    def __add__(self, right):
        if isinstance(right, Timecode):
            return self.from_frame( self.to_frame() + right.to_frame(), self._fps)
        if isinstance(right, int):
            return self.from_frame( self.to_frame() + right, self._fps)
        raise TypeError("Unsupported operand type for +" % str(type(right))[8:-2])

    def __radd__(self,left):
        return self.__add__(left)
    
    def __sub__(self, right):
        if isinstance(right, Timecode):
            return self.from_frame( self.to_frame() - right.to_frame(), self._fps)
        if isinstance(right, int):
            return self.from_frame( self.to_frame() - right, self._fps)
        raise TypeError("Unsupported operand type for -" % str(type(right))[8:-2])

    def __rsub__(self, left):
        return self.__sub__(left)
    
    def __str__(self):
        """
        String representation of this timecode
        """
        return  "%02d:%02d:%02d:%02d" % (
            self._hours, self._minutes, self._seconds, self._frames
        )














