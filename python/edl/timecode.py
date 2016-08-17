# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import decimal
from .errors import BadFrameRateError

# Some helpers to convert timecodes to frames, back and forth
def frame_from_timecode(timecode, fps=24):
    """
    Return the frame number for the given timecode at the given fps

    :param timecode: A timecode, either
        as a string in hh:mm:ss:ff format
        or as a (hours, minutes, seconds, frames) tuple
    :param fps : Number of frames per second
    :return: Corresponding frame number, as an int
    """
    if isinstance(timecode, str):
        (hour, minute, second, frame) = timecode.split(":")
    else:  # Assume a 4 elements tuple
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
    :return: A string in hh:mm:ss:ff format
    """

    # int values are casted to float with Decimal
    # to ensure we do real divisions and not C like integer divisions

    fps = decimal.Decimal(fps)

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
    """
    A non drop frame timecode
    """
    def __init__(self, timecode_string, fps=24):
        """
        Instantiate a timecode from a timecode or frame string.

        :param timecode_string: A timecode string in hh:mm:ss:ff format or
                                a frame number.
        """
        fields = timecode_string.split(":")
        if len(fields) != 4:
            try:
                # If we can convert the timecode_string to an int, assume we
                # have a frame and convert it to an absolute timecode using
                # our fps value. All calculations, etc from this point on treat
                # the input as if it was a timecode and not a frame.
                fields = timecode_from_frame(int(timecode_string), fps).split(":")
            except:
                raise ValueError(
                    "Given timecode %s can not be converted to hh:mm:ss:ff format." % timecode_string
                )
        self._fps = fps
        self._hours = int(fields[0])
        self._minutes = int(fields[1])
        self._seconds = int(fields[2])
        self._frames = int(fields[3])
        # Do some basic checks
        if self._frames >= self._fps:
            raise BadFrameRateError(self._frames, self._fps)
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
            (self._hours, self._minutes, self._seconds, self._frames), self._fps
        )

    def to_seconds(self):
        """
        Convert this timecode to seconds, using its frame rate

        :return: Number of seconds as a Decimal
        """
        frame = self.to_frame()
        return decimal.Decimal(frame) / self._fps

    # Redefine some standars operators
    def __add__(self, right):
        """
        + operator override : Add a timecode or a number of frames to this Timecode
        with the Timecode on the right of the operator

        :param right: Right operand for + operator, either a Timecode instance or an int
                representing a number of frames
        :return: A new Timecode instance, in this Timecode fps, result of the addition
        """
        if isinstance(right, Timecode):
            return self.from_frame(self.to_frame() + right.to_frame(), self._fps)
        if isinstance(right, int):
            return self.from_frame(self.to_frame() + right, self._fps)
        raise TypeError("Unsupported operand type for +" % str(type(right))[8:-2])

    def __radd__(self, left):
        """
        + operator override : Add a number of frames to this Timecode, with the
        Timecode on the left of the + operator

        :return: A new Timecode instance, in this Timecode fps, result of the addition
        """
        return self.__add__(left)

    def __sub__(self, right):
        """
        - operator override : Substract a timecode or a number of frames to this Timecode
        with the Timecode on the right of the operator

        :param right: Right operand for - operator, either a Timecode instance or an int
                representing a number of frames
        :return: A new Timecode instance, in this Timecode fps, result of the substraction
        """
        if isinstance(right, Timecode):
            return self.from_frame(self.to_frame() - right.to_frame(), self._fps)
        if isinstance(right, int):
            return self.from_frame(self.to_frame() - right, self._fps)
        raise TypeError("Unsupported operand type for -" % str(type(right))[8:-2])

    def __rsub__(self, left):
        """
        - operator override : Substract a number of frames to this Timecode, with the
        Timecode on the left of the - operator

        :return: A new Timecode instance, in this Timecode fps, result of the substraction
        """
        return self.__sub__(left)

    def __str__(self):
        """
        String representation of this timecode
        """
        return "%02d:%02d:%02d:%02d" % (
            self._hours, self._minutes, self._seconds, self._frames
        )
