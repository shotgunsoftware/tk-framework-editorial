# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
#
# Portions of this code are based on the original PyTimecode module published by
# Joshua Banton. Currently maintained as the timecode module:
# https://github.com/eoyilmaz/timecode
# https://pypi.python.org/pypi/timecode
# Copyright (c) 2014 Joshua Banton and PyTimeCode developers

import decimal
import re
from .errors import BadFrameRateError

DROP_FRAME_DELIMITER = ";"
NON_DROP_FRAME_DELIMITER = ":"

FRAMES_IN_ONE_MINUTE = 1800 - 2

FRAMES_IN_TEN_MINUTES = (FRAMES_IN_ONE_MINUTE * 10) - 2


# Some helpers to convert timecodes to frames, back and forth.
def frame_from_timecode(timecode, fps=24, drop=False):
    """
    Return the frame number for the given timecode.

    :param timecode: A timecode, either as a string in hh:mm:ss:ff format
                     or as a (hours, minutes, seconds, frames) tuple.
    :param fps: Number of frames per second.
    :param drop: Boolean determining whether timecode should use drop frame or not.
    :return: Corresponding frame number, as an int.
    """
    if drop and fps not in [29.97, 59.94]:
        raise NotImplementedError("Time code calculation logic only supports drop frame "
                                  "calculations for 29.97 and 59.94 fps.")

    if isinstance(timecode, str):
        hour, minute, second, frame = re.findall(r"\d{2}", timecode)
    else:  # Assume a 4 elements tuple
        hour, minute, second, frame = timecode
    hours = int(hour)
    minutes = int(minute)
    seconds = int(second)
    frames = int(frame)
    ffps = float(fps)

    if drop:
        # Number of drop frames is 6% of framerate rounded to nearest integer.
        drop_frames = int(round(ffps * .066666))
    else:
        drop_frames = 0

    # We don't need the exact framerate anymore, we just need it rounded to the
    # nearest integer.
    ifps = int(ffps)

    # Number of frames per hour (non-drop)
    hour_frames = ifps * 60 * 60

    # Number of frames per minute (non-drop)
    minute_frames = ifps * 60

    # Total number of minutes
    total_minutes = (60 * hours) + minutes

    frame_number = ((hour_frames * hours) + (minute_frames * minutes) +
                    (ifps * seconds) + frames) - \
                   (drop_frames * (total_minutes - (total_minutes // 10)))

    frames = frame_number + 1

    return frames


def timecode_from_frame(total_frames, fps=24, drop=False):
    """
    Return the timecode corresponding to the given frame.

    :param total_frames: A frame number, as an int.
    :param fps: Number of frames per seconds, as an int.
    :param drop: Boolean determining whether timecode should use drop frame or not.
    :returns: Timecode as string, e.g. '01:02:12:32' (non-drop frame) or
              '01:02:12;32' (drop frame)
    """
    if drop and fps not in [29.97, 59.94]:
        raise NotImplementedError("Time code calculation logic only supports drop frame "
                                  "calculations for 29.97 and 59.94 fps.")

    # For a good discussion around time codes and sample code, see
    # http://andrewduncan.net/timecodes/

    # Round fps to the nearest integer.
    # Note that for frame rates such as 29.97 or 59.94,
    # we treat them as 30 and 60 when converting to time code.
    # Then, in some cases we 'compensate' by adding 'drop frames',
    # e.g. jump in the time code at certain points to make sure that
    # the time code calculations are roughly right.
    #
    # For another good explanation, see
    # https://documentation.apple.com/en/finalcutpro/usermanual/index.html#chapter=D%26section=6
    fps = int(round(fps))

    if drop:
        # drop-frame-mode
        # add two 'fake' frames every minute but not every 10 minutes
        #
        # example at the one minute mark:
        #
        # frame: 1795 non-drop: 00:00:59:25 drop: 00:00:59;25
        # frame: 1796 non-drop: 00:00:59:26 drop: 00:00:59;26
        # frame: 1797 non-drop: 00:00:59:27 drop: 00:00:59;27
        # frame: 1798 non-drop: 00:00:59:28 drop: 00:00:59;28
        # frame: 1799 non-drop: 00:00:59:29 drop: 00:00:59;29
        # frame: 1800 non-drop: 00:01:00:00 drop: 00:01:00;02
        # frame: 1801 non-drop: 00:01:00:01 drop: 00:01:00;03
        # frame: 1802 non-drop: 00:01:00:02 drop: 00:01:00;04
        # frame: 1803 non-drop: 00:01:00:03 drop: 00:01:00;05
        # frame: 1804 non-drop: 00:01:00:04 drop: 00:01:00;06
        # frame: 1805 non-drop: 00:01:00:05 drop: 00:01:00;07
        #
        # example at the ten minute mark:
        #
        # frame: 17977 non-drop: 00:09:59:07 drop: 00:09:59;25
        # frame: 17978 non-drop: 00:09:59:08 drop: 00:09:59;26
        # frame: 17979 non-drop: 00:09:59:09 drop: 00:09:59;27
        # frame: 17980 non-drop: 00:09:59:10 drop: 00:09:59;28
        # frame: 17981 non-drop: 00:09:59:11 drop: 00:09:59;29
        # frame: 17982 non-drop: 00:09:59:12 drop: 00:10:00;00
        # frame: 17983 non-drop: 00:09:59:13 drop: 00:10:00;01
        # frame: 17984 non-drop: 00:09:59:14 drop: 00:10:00;02
        # frame: 17985 non-drop: 00:09:59:15 drop: 00:10:00;03
        # frame: 17986 non-drop: 00:09:59:16 drop: 00:10:00;04
        # frame: 17987 non-drop: 00:09:59:17 drop: 00:10:00;05

        # Calculate number of drop frames for a 29.97 standard NTSC workflow.
        ten_minute_chunks = total_frames / FRAMES_IN_TEN_MINUTES
        one_minute_chunks = total_frames % FRAMES_IN_TEN_MINUTES

        ten_minute_part = 18 * ten_minute_chunks
        one_minute_part = 2 * ((one_minute_chunks - 2) / FRAMES_IN_ONE_MINUTE)

        if one_minute_part < 0:
            one_minute_part = 0

        # Add extra frames
        total_frames += ten_minute_part + one_minute_part

        # for 60 fps drop frame calculations, we add twice the number of frames
        if fps == 60:
            total_frames *= 2

        # time codes are on the form 12:12:12;12
        frames_token = DROP_FRAME_DELIMITER

    else:
        # time codes are on the form 12:12:12:12
        frames_token = NON_DROP_FRAME_DELIMITER

    # now split our frames into time code
    hours = int(total_frames / (3600 * fps))
    minutes = int(total_frames / (60 * fps) % 60)
    seconds = int(total_frames / fps % 60)
    frames = int(total_frames % fps)

    return "%02d:%02d:%02d%s%02d" % (hours, minutes, seconds, frames_token, frames)


class Timecode(object):
    """
    A non-drop frame timecode.
    """
    def __init__(self, timecode_string, fps=24, drop=False):
        """
        Instantiate a timecode from a timecode or frame string.

        :param timecode_string: A timecode string in ``hh:mm:ss:ff`` format or
                                a frame number.
        :param fps: Frames per second setting
        :param drop: Boolean indicating whether to use drop frame or not.
        """
        # Split the timecode_string by any non-numeric delimiter.
        # This ensures that that we can support various formats of delimiting
        # timecode strings. For example:
        #   00:12:34:21 NON-DROP FRAME variation 1
        #   00:12:34.21 NON-DROP FRAME variation 2
        #   00:12:34;21 DROP FRAME variation 1
        #   00:12:34,21 DROP FRAME variation 2
        fields = re.findall(r"\d{2}", timecode_string)

        if len(fields) != 4:
            try:
                # If we can convert the timecode_string to an int, we assume we
                # have a frame number and convert it to an absolute timecode using
                # our fps value. All calculations, etc. from this point on treat
                # the input as if it was a timecode and not a frame.
                new_timecode_string = timecode_from_frame(int(timecode_string), fps, drop)
                fields = re.findall(r"\d{2}", new_timecode_string)
            except ValueError:
                raise ValueError(
                    "Given timecode %s can not be converted to hh:mm:ss:ff format." %
                    timecode_string
                )
        self._fps = fps
        self._hours = int(fields[0])
        self._minutes = int(fields[1])
        self._seconds = int(fields[2])
        self._frames = int(fields[3])
        self._drop = drop
        # use the "correct" frame token delimiter
        if self._drop:
            self._frame_delimiter = DROP_FRAME_DELIMITER
        else:
            self._frame_delimiter = NON_DROP_FRAME_DELIMITER

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
    def from_frame(cls, frame, fps=24, drop=False):
        """
        Return a new :class:`Timecode` for the given frame, at the given fps.

        :param frame: A frame number, as an :obj:`int`.
        :param fps: Number of frames per second, as an :obj:`int`.
        :param drop: Boolean indicating whether to use drop frame or not.
        :return: A :class:`Timecode` instance.
        """
        return Timecode(timecode_from_frame(frame, fps, drop), fps=fps, drop=drop)

    def to_frame(self):
        """
        Return the frame number corresponding to this :class:`Timecode` at the given fps.

        :return: A frame number, as an :obj:`int`.
        """
        return frame_from_timecode(
            (self._hours, self._minutes, self._seconds, self._frames), self._fps, self._drop
        )

    def to_seconds(self):
        """
        Convert this :class:`Timecode` to seconds, using its frame rate.

        :return: Number of seconds as a :obj:`Decimal`.
        """
        frame = self.to_frame()
        return decimal.Decimal(frame) / self._fps

    # Redefine some standard operators.
    def __add__(self, right):
        """
        + operator override: Add a timecode or a number of frames to this :class:`Timecode`
        with the :class:`Timecode` on the right of the operator.

        :param right: Right operand for ``+`` operator, either a :class:`Timecode` instance or an 
                      :obj:`int` representing a number of frames.
        :return: A new :class:`Timecode` instance, in this :class:`Timecode` fps, result of the 
                 addition.
        """
        if isinstance(right, Timecode):
            return self.from_frame(self.to_frame() + right.to_frame(), self._fps, self._drop)
        if isinstance(right, int):
            return self.from_frame(self.to_frame() + right, self._fps, self._drop)
        raise TypeError("Unsupported operand type %s for +" % type(right))

    def __radd__(self, left):
        """
        + operator override : Add a number of frames to this :class:`Timecode`, with the
        timecode on the left of the ``+`` operator.

        :param left: Left operand for ``+`` operator, either a :class:`Timecode` instance or an 
                     :obj:`int` representing a number of frames.
        :return: A new :class:`Timecode` instance, in this :class:`Timecode` fps, result of the 
                 addition.
        """
        return self.__add__(left)

    def __sub__(self, right):
        """
        - operator override : Subtract a timecode or a number of frames to this :class:`Timecode`
        with the timecode on the right of the operator.

        :param right: Right operand for ``-`` operator, either a :class:`Timecode` instance or an 
                      :obj:`int` representing a number of frames.
        :return: A new :class:`Timecode` instance, in this :class:`Timecode` fps, result of the 
                 subtraction.
        """
        if isinstance(right, Timecode):
            return self.from_frame(self.to_frame() - right.to_frame(), self._fps, self._drop)
        if isinstance(right, int):
            return self.from_frame(self.to_frame() - right, self._fps, self._drop)
        raise TypeError("Unsupported operand type %s for -" % type(right))

    def __rsub__(self, left):
        """
        - operator override : Subtract a number of frames to this :class:`Timecode`, with the
        timecode on the left of the ``-`` operator.

        :param left: Left operand for ``-`` operator, either a :class:`Timecode` instance or an 
                     :obj:`int` representing a number of frames.
        :return: A new :class:`Timecode` instance, in this :class:`Timecode` fps, result of the 
                 subtraction.
        """
        return self.__sub__(left)

    def __str__(self):
        """
        String representation of this :class:`Timecode` instance.
        """
        return "%02d:%02d:%02d%s%02d" % (
            self._hours, self._minutes, self._seconds, self._frame_delimiter, self._frames
        )
