# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

from .timecode import Timecode
import logging

class Edit(object):
    """
    An entry or event or edit from an edit list
    """
    def __init__(
        self,
        id      = None,
        reel    = None,
        channels    = None,
        source_in   = None,
        source_out  = None,
        record_in   = None,
        record_out  = None,
        fps         =  24,
    ):
        """
        Instantiate a new Edit

        :param id: The edit id in a Edit Decision list, as an int
        :param reel: The reel for this edit
        :param channels: Channels for this edit, video, audio, etc ...
        :param source_in: Timecode in for the source, as a hh:mm:ss:ff string
        :param source_out: Timecode out for the source, as a hh:mm:ss:ff string
        :param record_in: Timecode in for the recorder, as a hh:mm:ss:ff string
        :param record_out: Timecode out for the recorder, as a hh:mm:ss:ff string
        :param fps: Number of frames per second for this edit, as a hh:mm:ss:ff string
        """
        self._effect = []
        self._comments = []
        self._retime = None
        self._id = int(id)
        self._reel = reel
        self._channels = channels
        self._source_in = Timecode(source_in, fps=fps)
        self._source_out = Timecode(source_out, fps=fps)
        self._record_in = Timecode(record_in, fps=fps)
        self._record_out = Timecode(record_out, fps=fps)

    def add_effect(self, tokens):
        """
        For now, just register the effect line
        """
        self._effect.append( " ".join(tokens))

    def add_comments(self, comments):
        """
        Associate a comment line to this edit
        """
        self._comments.append(comments)

    def add_retime(self, tokens):
        """
        For now, just register the retime line
        """
        self._retime = " ".join(tokens)

    def __str__(self):
        return "%03d %s %s %s %s %s %s %s" % (
            self._id,
            self._reel,
            self._channels,
            "C",
            str(self._source_in),
            str(self._source_out),
            str(self._record_in),
            str(self._record_out),
        )
class EditList(object):
    def __init__(self, fps=24, logger=None):
        """
        Instantiate a new Edit Decision List
        
        :param fps: Number of frames per second for this EditList
        :param logger: A standard logging logger
        """
        
        self._title = None
        self._edits = []
        self._fps = fps
        self._logger = logger or logging.getLogger(__name__)

    def read_cmx_edl(self, path, locators_parser=None):
        """
        Parse the given edl file, extract a list of versions that need to be
        created
        http://xmil.biz/EDL-X/CMX3600.pdf
        http://www.scottsimmons.tv/blog/2006/10/12/how-to-read-an-edl/
        """
        # Reset defaut values
        self._title = None
        self._edits = []
        # And read the file
        self._logger.info("Parsing EDL %s" % path)
        with open(path, "rU") as handle:
            title = ""
            versions = []
            edit = None
            try:
                for line in handle.read().split("\n"):
                    # Not sure why we have to do that ...
                    # Some crappy Windows thing ?
                    line = line.replace("\x1a", "").strip()
                    if not line:
                        continue

                    self._logger.debug("Treating : [%s]" % line)
                    line_tokens = line.split()
                    if line.startswith("TITLE:"):
                        self._title = line_tokens[-1]
                    elif line.startswith("FCM:"):
                        # Can be DROP FRAME or NON DROP FRAME
                        if line_tokens[1] == "DROP FRAME":
                            raise NotImplementedError(
                                "Drop frame is not handled by this module"
                            )
                    elif line_tokens[0].startswith("*"):
                        # A comment
                        if edit :
                            edit.add_comments(line)
                            if locators_parser:
                                # Blindly call the parser with current edit and tokens
                                locators_parser(edit, line_tokens)
                    elif line_tokens[0] == "M2": # Retime
                        if not edit:
                            raise RuntimeError(
                                "Found unexpected line"
                            )
                        edit.add_retime(line_tokens)
                    elif line_tokens[0].isdigit():
                        # New edit
                        type = line_tokens[3]
                        if type == "C": # cut
                            # Number of tokens can vary in the middle
                            # so tokens at the end of the line are indexed with
                            # negative indexes
                            edit = Edit(
                                id          = int(line_tokens[0]),
                                reel        = line_tokens[1],
                                channels    = line_tokens[2],
                                source_in   = line_tokens[-4],
                                source_out  = line_tokens[-3],
                                record_in   = line_tokens[-2],
                                record_out  = line_tokens[-1],
                            )
                            self._edits.append(edit)
                        else:
                            if not edit:
                                raise RuntimeError(
                                    "Found unexpected effect"
                                )
                            edit.add_effect(line_tokens)

            except Exception, e:  # Catch the exception so we can add the current line contents
                args = ["%s while parsing %s at line\n%s" % (e.args[0], path, line)] + list(e.args[1:])
                e.args = args
                raise
