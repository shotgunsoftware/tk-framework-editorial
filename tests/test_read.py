# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import unittest2 as unittest
from edl import edl
import logging

class TestRead(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestRead,self).__init__(*args, **kwargs)
        self._edl_examples = []

    def setUp(self):
        resources_dir = os.path.join(os.path.dirname(__file__), "resources")
        for f in os.listdir(resources_dir):
            if f.endswith(".edl"):
                self._edl_examples.append(os.path.join(resources_dir, f))

    def read_edl_file(self, file):
        print "Reading %s" % file
        tc = edl.EditList()
        tc.read_cmx_edl(file)
        for edit in tc._edits:
            print edit

    def test_read_all_files(self):
        # Try to read all edls from resources directory
        for f in self._edl_examples:
            self.read_edl_file(f)

    def dummy_visitor(self, edit):
        print "Visiting %s" % str(edit)
        print "Comments are %s :\n" % "\n".join(edit.comments)

    def test_visitor(self):
        tc = edl.EditList()
        tc.read_cmx_edl(self._edl_examples[0], visitor=self.dummy_visitor)
