# Copyright (c) 2014 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


# Some particular errors / exceptions apps might want to catch and handle


class BadFrameRateError(ValueError):
    """
    Thin wrapper around ValueError for frame rate errors, allowing them to be
    caught easily
    """
    # Standard error message for bad frame rate errors
    __ERROR_MSG = ( "Invalid frame value [%d], it must be smaller than the "
                    "specified frame rate [%d]." )

    def __init__(self, frame_value, frame_rate, *args, **kwargs):
        """
        Instantiate a new BadFrameRateError, setting a standard error message from
        the given frame value and frame rate.

        :param frame_value: An integer, the frame value which caused the error.
        :param frame_rate: An integer, the frame rate for which the frame value 
                           caused the error.
        """
        super(BadFrameRateError, self).__init__(
            self.__ERROR_MSG % (frame_value, frame_rate),
            *args,
            **kwargs
            )



class UnsupportedEDLFeature(NotImplementedError):
    """
    Base class for all exceptions related to EDL features not being supported by 
    the current implementation.

    If needed, more specific Exceptions can be implemented by just deriving from
    this class and changing the error message.
    """
    __ERROR_MSG = "%s uses some EDL features which are not currently supported"
    def __init__(self, edl_name, *args, **kwargs):
        """
        Instantiate a new UnsupportedFeature.

        :param edl_name: A string, the EDL file name.
        """
        super(UnsupportedEDLFeature, self).__init__(
            self.__ERROR_MSG % edl_name,
            *args,
            **kwargs
        )

# Some specific exceptions for most common missing features encoutered in production
class BadBLError(UnsupportedEDLFeature):
    """
    Thin wrapper around UnsupportedEDLFeature for BL errors, allowing them
    to be caught easily.
    """
    __ERROR_MSG = "%s has a black slug (BL) event, which are not supported."


class BadDropFrameError(UnsupportedEDLFeature):
    """
    Thin wrapper around UnsupportedEDLFeature for drop frame errors, allowing them
    to be caught easily
    """
    __ERROR_MSG = ( "%s uses drop frame timecode. Currently, only non-drop "
                    "frame timecodes are supported." )

