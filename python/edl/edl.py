# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

from .timecode import Timecode
from . import logger
import os

class Edit(object):
    """
    An entry, or event, or edit from an edit list
    
    New attributes can be added at runtime, provided that they don't
    clash with Edit regular attributes, by just setting their value, e.g.
    edit.my_own_attribute = "awesome"
    They then are accessible like other regular attributes, e.g.
    print edit.my_own_attribute

    """
    def __init__(
        self,
        id          = None,
        reel        = None,
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
        self._meta_data = {} # A place holder where additional meta data can be stored
        self._retime = None
        self._id = int(id)
        self._reel = reel
        self._channels = channels
        self._source_in = Timecode(source_in, fps=fps)
        self._source_out = Timecode(source_out, fps=fps)
        self._record_in = Timecode(record_in, fps=fps)
        self._record_out = Timecode(record_out, fps=fps)

    @property
    def id(self):
        """
        Return the id for this edit
        """
        return self._id

    @property
    def comments(self):
        """
        Return the comments for this edit, as a list
        """
        return self._comments

    @property
    def timecodes(self):
        """
        Return the source in, source out, record in, record out timecodes for this
        edit as a tuple.
        """
        return (
            self._source_in,
            self._source_out,
            self._record_in,
            self._record_out
        )

    @property
    def source_in(self):
        """
        Return the source in timecode for this edit
        """
        return self._source_in

    @property
    def source_out(self):
        """
        Return the source out timecode for this edit
        """
        return self._source_out

    @property
    def source_duration(self):
        """
        Return the source duration, in frames
        """
        # Timecode out are exclusive, e.g.
        # 00:00:00:01 -> 00:00:00:02 is only one frame long
        return self._source_out.to_frame() - self._source_in.to_frame()

    @property
    def record_in(self):
        """
        Return the record in timecode for this edit
        """
        return self._record_in

    @property
    def record_out(self):
        """
        Return the record out timecode for this edit
        """
        return self._record_out

    @property
    def record_duration(self):
        """
        Return the record duration, in frames
        """
        # Timecode out are exclusive, e.g.
        # 00:00:00:01 -> 00:00:00:02 is only one frame long
        return self._record_out.to_frame() - self._record_in.to_frame()

    @property
    def has_effect(self):
        """
        Return True if this edit has some effect(s)
        """
        return bool(self._effects)

    def add_effect(self, tokens):
        """
        For now, just register the effect line
        Later we might want to parse the tokens, and store some actual
        effects value on this edit
        """
        self._effect.append( " ".join(tokens))

    def add_comments(self, comments):
        """
        Associate a comment line to this edit
        """
        self._comments.append(comments)

    @property
    def has_retime(self):
        """
        Return True if this edit has some retime
        """
        return bool(self._retime)

    def add_retime(self, tokens):
        """
        For now, just register the retime line
        Later we might want to parse the tokens, and store some actual
        retime values
        """
        self._retime = " ".join(tokens)

    def __str__(self):
        """
        String representation for this Edit
        """
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
    def __setarr__(self, attr_name, value):
        """
        Allow new attributes to be added on the fly, e.g. when parsing a file
        with a visitor
        
        :param attr_name: Name of the attribute that needs setting
        :param value: The value the attribute should take
        """
        if hasattr(self, attr_name):
            object.__setattr__(self, name, value)
        else:
            self._meta_data[attr_name] = value

    def __getattr__(self, attr_name):
        """
        Retrieve runtime attributes from meta_data dictionary
        
        :param attr_name: An attribute name
        :return: The value for the given attribute name
        :raise: AttributeError if the attribute can't be found
        """
        if attr_name in self._meta_data:
            return self._meta_data[attr_name]
        raise AttributeError("Edit has no attribute %s" % attr_name)

class EditList(object):
    """
    An Edit Decision List
    
    Typical use of EditList could look like that :
    
    # Define a visitor to extract some extra information from comments or locators
    def edit_parser(edit):
        # New attributes can be added on the fly
        if edit.id % 2:
            edit.is_even = False
        else:
            edit.is_even = True

    edl = EditList(file_path="/tmp/my_edl.edl", visitor=edit_parser)
    for edit in edl.entries:
        print str(edit)
        # Added attributes are reachable like regular ones
        print edit.is_even
    """

    __logger = logger.get_logger()

    def __init__(self, fps=24, file_path=None, visitor=None):
        """
        Instantiate a new Edit Decision List
        
        :param fps: Number of frames per second for this EditList
        :file_path: Full path to a file to read
        """
        
        self._title = None
        self._edits = []
        self._fps = fps
        if file_path:
            _, ext = os.path.splitext(file_path)
            if ext != ".edl":
                raise NotImplementedError(
                    "Can't read %s : don't know how to read files with %s extension",
                    file_path,
                    ext
                )
            self.read_cmx_edl(file_path, visitor)

    @property
    def edits(self):
        """
        Return a list of all edits in this EditList
        """
        return self._edits

    @property
    def title(self):
        """
        Return this EditList's title
        """
        return self._title

    @property
    def fps(self):
        """
        Return the number of frame per seconds used by this EditList
        """
        return self._fps

    def read_cmx_edl(self, path, visitor=None):
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
        self.__logger.info("Parsing EDL %s" % path)
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

                    self.__logger.debug("Treating : [%s]" % line)
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
                    elif line_tokens[0] == "M2": # Retime
                        if not edit:
                            raise RuntimeError(
                                "Found unexpected line"
                            )
                        edit.add_retime(line_tokens)
                    elif line_tokens[0].isdigit():
                        # New edit
                        # Time to call the visitor ( if any ) with the previous
                        # edit ( if any )
                        if edit and visitor:
                            visitor(edit)
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
                    # Call the visitor ( if any ) with the last edit ( if any )
                    if edit and visitor:
                        visitor(edit)
            except Exception, e:  # Catch the exception so we can add the current line contents
                args = ["%s while parsing %s at line\n%s" % (e.args[0], path, line)] + list(e.args[1:])
                e.args = args
                raise
