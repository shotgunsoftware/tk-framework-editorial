# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.
#

import decimal
import re
from .errors import BadFrameRateError

DROP_FRAME_DELIMITER = ";"
NON_DROP_FRAME_DELIMITER = ":"


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
        # This supports timecode up to 999:59:59:59.
        hour, minute, second, frame = Timecode.parse_timecode(timecode)
    else:  # Assume a 4 elements tuple
        hour, minute, second, frame = timecode
    hours = int(hour)
    minutes = int(minute)
    seconds = int(second)
    frames = int(frame)

    if drop:
        # Number of drop frames per minute is 6% of framerate rounded to nearest integer.
        drop_frames_per_minute = int(round(fps * .066666))
    else:
        drop_frames_per_minute = 0

    # We don't need the exact framerate anymore if we're using drop frame, we just need it
    # rounded to nearest integer. Non-drop frame will return the same value.
    fps_int = int(round(fps))
    # Number of frames per hour (non-drop)
    frames_per_hour = fps_int * 60 * 60
    # Number of frames per minute (non-drop)
    frames_per_minute = fps_int * 60
    # Total number of minutes (non-drop)
    total_minutes = (60 * hours) + minutes

    # Put it all together.
    frame_number = (frames_per_hour * hours) + (frames_per_minute * minutes) + \
        (fps_int * seconds) + frames
    # If we're using drop frame, calculate the total frames to drop by multiplying the number of
    # frames we drop each minute, by the total number of minutes MINUS the number of 10-minute
    # intervals.
    frames_to_drop = drop_frames_per_minute * (total_minutes - (total_minutes / 10))
    # Subtract any frames to drop to get our final frame number.
    frame_number -= frames_to_drop

    return frame_number


def timecode_from_frame(frame_number, fps=24, drop=False):
    """
    Return the timecode corresponding to the given frame.

    :param frame_number: A frame number, as an int.
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
    fps_int = int(round(fps))

    if drop:
        # drop-frame-mode
        # for 30 fps jump 2 frames every minute but not every 10 minutes
        # for 60 fps jump 4 frames every minute but not every 10 minutes
        #
        # D = Drop Frame
        # ND = Non-Drop Frame
        #
        # Example at the one minute / 30-sec mark:
        #             30 fps                         60 fps
        # -------------------------------------------------------------------------
        # frame: 1798 ND: 00:00:59:28 D: 00:00:59;28 ND: 00:00:29:58 D: 00:00:29;58
        # frame: 1799 ND: 00:00:59:29 D: 00:00:59;29 ND: 00:00:29:59 D: 00:00:29;59
        # frame: 1800 ND: 00:01:00:00 D: 00:01:00;02 ND: 00:00:30:00 D: 00:00:30;00
        # frame: 1801 ND: 00:01:00:01 D: 00:01:00;03 ND: 00:00:30:01 D: 00:00:30;01
        # frame: 1802 ND: 00:01:00:02 D: 00:01:00;04 ND: 00:00:30:02 D: 00:00:30;02
        #
        # example at the two minute / one minute mark:
        #
        # frame: 3598 ND: 00:01:59:28 D: 00:01:59;28 ND: 00:00:59:58 D: 00:00:59:58
        # frame: 3599 ND: 00:01:59:29 D: 00:01:59;29 ND: 00:00:00:59 D: 00:00:59:59
        # frame: 3600 ND: 00:02:00:00 D: 00:02:00;02 ND: 00:01:00:00 D: 00:01:00;04
        # frame: 3601 ND: 00:02:00:01 D: 00:02:00;03 ND: 00:01:00:01 D: 00:01:00;05
        # frame: 3602 ND: 00:02:00:02 D: 00:02:00;04 ND: 00:01:00:02 D: 00:01:00;06
        #
        # examples at the ten minute / 5 minute marks:
        #
        # frame: 17980 ND: 00:09:59:10 D: 00:09:59;28  ND: 00:04:59:40 D: 00:04:59;56
        # frame: 17981 ND: 00:09:59:11 D: 00:09:59;29  ND: 00:04:59:41 D: 00:04:59;57
        # frame: 17982 ND: 00:09:59:12 D: 00:10:00;00  ND: 00:04:59:42 D: 00:04:59;58
        # frame: 17983 ND: 00:09:59:13 D: 00:10:00;01  ND: 00:04:59:43 D: 00:04:59;59
        # frame: 17984 ND: 00:09:59:14 D: 00:10:00;02  ND: 00:04:59:44 D: 00:05:00;04

        # frame: 17998 ND: 00:09:59:58 D: 00:10:00;16  ND: 00:04:59:58 D: 00:05:00;18
        # frame: 17999 ND: 00:09:59:59 D: 00:10:00;17  ND: 00:04:59:59 D: 00:05:00;19
        # frame: 18000 ND: 00:10:00:00 D: 00:10:00;18  ND: 00:05:00:00 D: 00:05:00;20
        # frame: 18001 ND: 00:10:00:01 D: 00:10:00;19  ND: 00:05:00:01 D: 00:05:00;21
        # frame: 18002 ND: 00:10:00:02 D: 00:10:00;20  ND: 00:05:00:02 D: 00:05:00;22

        # Number of frames to drop on the minute marks is the nearest integer to 6%
        # of the framerate.
        # 30fps: 2
        # 60fps: 4
        drop_frames = int(round(fps * .066666))

        # Number of NON-DROP frames per ten minutes
        # 30fps: 30 * 60 * 10 = 17982
        # 60fps: 60 * 60 * 10 = 35964
        frames_per_10_mins = int(round(fps * 60 * 10))

        # Total number of DROP frames per minute
        # fps * 60 (seconds) - (# drop frames per minute)
        # 30fps: 30 * 60 - 2 = 1798
        # 60fps: 60 * 60 - 4 = 3596
        frames_per_min = (int(round(fps)) * 60) - drop_frames

        # Number of frames to add per 10 minute chunk
        # (# frames to drop per minute) * 9 (9 minutes since every 10th minute we *don't* drop)
        # 30fps: 2 * 9 = 18
        # 60fps: 4 * 9 = 36
        additional_frames_per_10m = drop_frames * 9

        # number of frames to add per 1 minute chunk
        # 30fps: 2
        # 60fps: 4
        additional_frames_per_1m = drop_frames

        # Number of 10-minute chunks of frames
        ten_minute_chunks = frame_number / frames_per_10_mins
        # Remainder of frames after splitting into 10 minute chunks
        remaining_frames = frame_number % frames_per_10_mins

        if remaining_frames > drop_frames:
            add_frames = (additional_frames_per_10m * ten_minute_chunks) + \
                (additional_frames_per_1m *
                    ((remaining_frames - drop_frames) / frames_per_min))
        else:
            add_frames = additional_frames_per_10m * ten_minute_chunks

        # The final result!
        frame_number += add_frames

        # Drop frame time codes use a ; to delimit the frames by convention.
        frames_token = DROP_FRAME_DELIMITER

    else:
        # Non-drop frame time codes use a : to delimit the frames by convention.
        frames_token = NON_DROP_FRAME_DELIMITER

    # Now split our frames into timecode.
    hours = int(frame_number / (3600 * fps_int))
    minutes = int(frame_number / (60 * fps_int) % 60)
    seconds = int(frame_number / fps_int % 60)
    frames = int(frame_number % fps_int)

    return "%02d:%02d:%02d%s%02d" % (hours, minutes, seconds, frames_token, frames)


class Timecode(object):
    """
    A non-drop frame timecode object.
    """
    def __init__(self, timecode_string, fps=24, drop=False):
        """
        Instantiate a Timecode from a timecode or frame string.

        :param timecode_string: A timecode string in ``hh:mm:ss:ff`` format or
                                a frame number.
        :param fps: Frames per second setting as an int or float.
        :param drop: Boolean indicating whether to use drop frame or not.
        """
        # Split the timecode_string by any non-numeric delimiter.
        # This ensures that that we can support various formats of delimiting
        # timecode strings. For example:
        #   00:12:34:21 NON-DROP FRAME variation 1
        #   00:12:34.21 NON-DROP FRAME variation 2
        #   00:12:34;21 DROP FRAME variation 1
        #   00:12:34,21 DROP FRAME variation 2
        try:
            self._hours, self._minutes, self._seconds, self._frames = \
                self.parse_timecode(timecode_string)
        except ValueError:
            # If we can convert the timecode_string to an int, we assume we
            # have a frame number and convert it to an absolute timecode using
            # our fps value. All calculations, etc. from this point on treat
            # the input as if it was a timecode and not a frame.
            try:
                new_timecode_string = timecode_from_frame(int(timecode_string), fps, drop)
                self._hours, self._minutes, self._seconds, self._frames = \
                    self.parse_timecode(new_timecode_string)
            except ValueError:
                raise ValueError("Timecode %s can not be converted to hh:mm:ss:ff format." %
                                 timecode_string)

        self._fps = fps
        self._drop = drop
        # use the "correct" frame token delimiter
        if self._drop:
            self._frame_delimiter = DROP_FRAME_DELIMITER
        else:
            self._frame_delimiter = NON_DROP_FRAME_DELIMITER

        # Do some basic checks
        # Note: I think we need to support non-standard timecodes > 24 hours for
        #       example 103:12:33:07. Assuming this is confirmed, we should remove the
        #       code below.
        # if self._hours > 23:
        #     raise ValueError(
        #         "Invalid hours value %d, it must be smaller than 24" % self._hours
        #     )
        if self._minutes > 59:
            raise ValueError(
                "Invalid minutes value %d, it must be smaller than 60" % self._minutes
            )
        if self._seconds > 59:
            raise ValueError(
                "Invalid seconds value %d, it must be smaller than 60" % self._seconds
            )
        if self._frames >= self._fps:
            raise BadFrameRateError(self._frames, self._fps)

    @classmethod
    def parse_timecode(cls, timecode_str):
        """
        Parse a timecode string to valid hour, minute, second, and frame values.

        :param timecode_str: A timecode string in ``hh:mm:ss:ff`` format.
        :return: tuple of (hours, minutes, seconds, frames) where all values are ints.
        :raises: ValueError if string cannot be parsed.
        """
        fields = re.findall(r"\d{2,3}", timecode_str)

        if len(fields) != 4:
            raise ValueError("Timecode is not in a valid hh:mm:ss:ff format.")

        try:
            tc_tuple = (int(fields[0]), int(fields[1]), int(fields[2]), int(fields[3]),)
        except IndexError:
            raise ValueError("Timecode is not in a valid hh:mm:ss:ff format.")

        return tc_tuple

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

    def __repr__(self):
        """
        Code representation of this :class:`Timecode` instance.
        """
        drop = "ND"
        if self._drop:
            drop = "D"
        return "<class %s %02d:%02d:%02d%s%02d (%sfps %s)>" % (
            self.__class__.__name__, self._hours, self._minutes, self._seconds,
            self._frame_delimiter, self._frames, self._fps, drop
        )
