# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import logging

class FrameworkLogHandler(logging.StreamHandler):
    def __init__(self, framework, *args, **kwargs):
        super(FrameworkLogHandler, self).__init__(*args, **kwargs)
        self._framework = framework

    def emit(self, record):
        if self._framework:
            if record.levelno == logging.INFO:
                self._framework.log_info(record.getMessage())
            elif record.levelno == logging.INFO:
                self._framework.log_debug(record.getMessage())
            elif record.levelno == logging.WARNING:
                self._framework.log_warning(record.getMessage())
            elif record.levelno == logging.ERROR:
                self._framework.log_warning(record.getMessage())
        #super(FrameworkLogHandler, self).emit(record)

def get_logger(level=logging.INFO):
    """
    Retrieve a logger
    """
    logger_parts = __name__.split(".")
    print str(logger_parts)
    if len(logger_parts) > 1:
        # Remove the last part which should be this file
        # name
        logger_name = ".".join(logger_parts[:-1])
    else:
        logger_name = logger_parts[0]
    logger = logging.getLogger(logger_name)
    # Check if we running this module from a Toolkit
    # framework. The only dependency we have with Toolkit
    # if for logging, so it's worth trying to allow using
    # this module from non Toolkit apps, using regular Python
    # imports
    try:
        import sgtk
        # Raising an exception will activate the except clause
        framework = sgtk.platform.current_bundle()
        if not framework :
            raise Exception("No framework")
        logger.addHandler(FrameworkLogHandler(framework))
        logger.setLevel(level)
    except:
        # Default to basic logging
        logging.basicConfig(level=level)
    return logger
