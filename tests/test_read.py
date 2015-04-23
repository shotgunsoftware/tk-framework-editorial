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

    def dummy_visitor(self, edit, logger):
        logger.info("Visiting %s" % str(edit))
        logger.info("Comments are :\n\t%s" % "\n\t".join(edit.comments))
        # Test if adding a runtime attribute works
        edit.private_id = edit.id

    def test_visitor(self):
        tc = edl.EditList()
        tc.read_cmx_edl(self._edl_examples[0], visitor=self.dummy_visitor)
        for edit in tc.edits:
            self.assertEqual(edit.private_id, edit.id)

    def advanced_visitor(self, edit, logger):
        edl.process_edit(
            edit,
            logger,
            shot_regexp="(?P<shot_name>\w+)_(?P<type>\w\w\d\d)_(?P<version>[V,v]\d+)$"
        )

    def test_standard_visitor(self):
        # Make sure we are able to read all examples
        for f in self._edl_examples:
            tc = edl.EditList()
            tc.read_cmx_edl(f, visitor=edl.process_edit)

    def test_class_visitor(self):
        processor = edl.EditProcessor()
        # Make sure we are able to read all examples
        for f in self._edl_examples:
            tc = edl.EditList()
            tc.read_cmx_edl(f, visitor=processor.process)

    def test_advanced_visitor(self):
        # Check we are able to extract expected information from a well known
        # example
        path = os.path.join(os.path.dirname(__file__), "resources", "scan_request_test.edl")
        tc = edl.EditList(
            file_path=path,
            visitor=self.advanced_visitor,
        )
        for edit in tc.edits:
            self.assertIsNotNone(edit._shot_name)
            self.assertIsNotNone(edit._name)
            self.assertEqual(edit._asc_sat, "asat%d" % edit.id)
            self.assertEqual(edit._asc_sop, "asop%d" % edit.id)
            self.assertEqual(edit._version, "V0001")
            self.assertEqual(edit._name, "%s_%s_%s" % (edit._shot_name, edit._type, edit._version))
            # All comments in this example include known keywords
            # so the very first call to next should raise a StopIteration
            with self.assertRaises(StopIteration):
                edit.pure_comments.next()


    def failing_property_override(self, edit, logger):
        edit.id = "foo"

    def test_accessor_overrides(self):
        with self.assertRaises(AttributeError) as cm:
            for f in self._edl_examples:
                tc = edl.EditList(
                    file_path=f,
                    visitor=self.failing_property_override,
                )


