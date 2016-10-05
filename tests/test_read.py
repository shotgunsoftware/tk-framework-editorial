# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.
#
import os
import decimal
import unittest2 as unittest
from edl import edl
from edl import timecode, BadDropFrameError, BadBLError, UnsupportedEDLFeature, BadFrameRateError
import logging
import re


class TestRead(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestRead, self).__init__(*args, **kwargs)
        self._edl_examples = []
        self._unsupported_examples = []
        self._unsupported_dir = None

    def setUp(self):
        resources_dir = os.path.join(os.path.dirname(__file__), "resources")
        for f in os.listdir(resources_dir):
            if f.endswith(".edl"):
                self._edl_examples.append(os.path.join(resources_dir, f))

        self._unsupported_dir = os.path.join(resources_dir, "unsupported")
        for f in os.listdir(self._unsupported_dir):
            if f.endswith(".edl"):
                self._unsupported_examples.append(os.path.join(self._unsupported_dir, f))

        # Set up some reference data that we'll compare against in our conversion tests.
        # Note: drop frame timecode uses ; as the frame delimiter
        self._frames_timecode_map = [
            (24, False, 1234567, "14:17:20:07"),
            (24, False, 2345678, "27:08:56:14"),
            (24, False, 12345678, "142:53:23:06"),
            (24, False, 23456789, "271:29:26:05"),
            (30, False, 1234567, "11:25:52:07"),
            (30, False, 2345678, "21:43:09:08"),
            (30, False, 12345678, "114:18:42:18"),
            (30, False, 23456789, "217:11:32:29"),
            (60, False, 1234567, "05:42:56:07"),
            (60, False, 2345678, "10:51:34:38"),
            (60, False, 12345678, "57:09:21:18"),
            (60, False, 23456789, "108:35:46:29"),
            (29.97, True, 1234567, "11:26:33;13"),
            (29.97, True, 2345678, "21:44:27;16"),
            (29.97, True, 12345678, "114:25:34;16"),
            (29.97, True, 23456789, "217:24:35;19"),
            (59.94, True, 1234567, "05:43:16;43"),
            (59.94, True, 2345678, "10:52:13;46"),
            (59.94, True, 12345678, "57:12:47;14"),
            (59.94, True, 23456789, "108:42:17;49"),
        ]

    def read_edl_file(self, file):
        logging.info("Reading %s" % file)
        tc = edl.EditList()
        tc.read_cmx_edl(file)
        for edit in tc._edits:
            logging.info(edit)
            for c in edit.pure_comments:
                # Check that pure comments are pure and do not contain
                # known keywords
                self.assertIsNone(edl._COMMENT_REGEXP.match(c))

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

    def test_pure_comments(self):
        path = os.path.join(os.path.dirname(__file__), "resources", "ER_00119_with_comments.edl")
        tc = edl.EditList(file_path=path)
        for edit in tc.edits:
            for c in edit.pure_comments:
                self.assertIsNotNone(re.search("this_is_a_pure_comment", c))

    def test_comments(self):
        """
        Parses a file with comment information and checks for expected values.
        """
        # Edls and their expected comment values.
        comment_edls = {
                        "079_HA_006.edl": ["*079_HA_0010",
                                           "*FROM CLIP NAME:  V8033-14_SC65 NB MOS*",
                                           "*SOURCE FILE: N005_C020_11099E"],
                        "audio-at-end.edl": ["* FROM CLIP NAME: mad.men.714.hdtv-lol.mp4"],
                        "cut_import_example.edl": ["* FROM CLIP NAME:  204_CTE_0005_CMP_V0003.MOV",
                                                   "* LOC: 01:00:00:12 YELLOW  001_001"],
                        "DD_509_LOCKED_VFX_LINK.edl": ["LOC: 00:00:01:00 YELLOW DD509_0010|D:464"],
                        "EDL_Colors_v4.EDL": ["Sh_0010_CYAN", "FROM CLIP NAME: CYAN"],
                        "ER_00119_with_comments.edl": ["* FROM CLIP NAME:  VYD31C-3",
                                                       "* LOC: 01:01:03:00 YELLOW  YA0010",
                                                       "* SOURCE FILE: A502_C014_0327NX",
                                                       "* ========================================================this_is_a_pure_comment",
                                                       "* All pure comments in this file should be tagged with \"this_is_a_pure_comment\"",
                                                       "* this_is_a_pure_comment",
                                                       "* this_is_a_pure_comment",
                                                       "* this_is_a_pure_comment",
                                                       "* ========================================================this_is_a_pure_comment",
                                                       "* foo bar blah this_is_a_pure_comment",
                                                       "* COMMENT :foo bar blah this_is_a_pure_comment"],
                        "HSM_SATL_v001_shotNameNote.edl": ["*HSM_SATL_0010"],
                        "MessyTL_clean.EDL": ["FROM CLIP NAME: 4b",
                                              "TO CLIP NAME: 2a",
                                              "* UNSUPPORTED EFFECT:0 RESIZE",
                                              "* UNSUPPORTED EFFECT:1 COLOUR CORRECTON",
                                              "* UNSUPPORTED EFFECT:1 RESIZE",
                                              "DLEDL: FOCUS_DESCR CENTERED"],
                        "pxy5.edl": ["* FROM CLIP NAME:  GJ_2_LAYOUT_SC011_003_WZ_0606.MOV",
                                     "* COMMENT:"],
                        "raphe_temp1_rfe_R01_v01_TRANSITIONS.edl": ["* FROM CLIP NAME: Transparent Video"],
                        "scan_request_test.edl": ["*FROM CLIP NAME: 053_CSC_0750_PC01_V0001",
                                                  "*ASC_SOP: asop1",
                                                  "*ASC_SAT: asat1",
                                                  "* LOC: 00:00:02:19 YELLOW  053_CSC_0750_PC01_V0001 997 // 8-8 Match to edit"]
                        }
        for comment_edl in comment_edls:
            path = os.path.join(os.path.dirname(__file__), "resources", comment_edl)
            tc = edl.EditList(file_path=path)
            for edit, item in enumerate(tc.edits):
                self.assertEqual(item.comments, comment_edls[comment_edl])
                break

    def test_transitions(self):
        """
        Parses a file with transition information and checks an edit event with
        Transitions at the head and tail for expected values.
        """
        trans_edls = ["raphe_temp1_rfe_R01_v01_TRANSITIONS.edl"]
        for trans_edl in trans_edls:
            path = os.path.join(os.path.dirname(__file__), "resources", trans_edl)
            tc = edl.EditList(file_path=path)
            for edit, item in enumerate(tc.edits):
                if item.id == 2:
                    self.assertEqual(str(item.source_in), str(timecode.Timecode("00:59:59:09")))
                    self.assertEqual(str(item.source_out), str(timecode.Timecode("01:00:05:15")))
                    self.assertEqual(str(item.record_in), str(timecode.Timecode("01:00:07:23")))
                    self.assertEqual(str(item.record_out), str(timecode.Timecode("01:00:14:05")))

    def test_frames_input(self):
        """
        Parses a file with source_in and source_out represented as frames and
        not timecode. Checks to make sure frames have been converted to the
        expected value.
        """
        frames_edls = ["jrun_demo_relative_frames1.edl"]
        for frame_edl in frames_edls:
            path = os.path.join(os.path.dirname(__file__), "resources", frame_edl)
            tc = edl.EditList(file_path=path)
            for edit, item in enumerate(tc.edits):
                self.assertEqual(str(item.source_in), str(timecode.Timecode("00:00:00:09")))
                self.assertEqual(str(item.source_out), str(timecode.Timecode("00:00:02:16")))
                break

    def test_ignore_audio(self):
        """
        Parses files with Audio entry events. If audio events are found and not
        ignored, more than 2 events will be found. Test succeeds if no more than
        2 events are found.
        """
        audio_edls = ["audio-at-end.edl", "audio-follows-video.edl", "audio-separately.edl"]
        for audio_edl in audio_edls:
            path = os.path.join(os.path.dirname(__file__), "resources", audio_edl)
            tc = edl.EditList(file_path=path)
            for edit, item in enumerate(tc.edits):
                self.assertLess(edit, 2)

    def failing_property_override(self, edit, logger):
        edit.id = "foo"

    def test_accessor_overrides(self):
        with self.assertRaises(AttributeError) as cm:
            for f in self._edl_examples:
                edl.EditList(
                    file_path=f,
                    visitor=self.failing_property_override,
                )

    def test_tc_round_trip(self):
        # We need to make sure tc values aren't mutated when going back and
        # forth from tc to frames to tc
        tc = "01:02:03:04"
        frame = timecode.frame_from_timecode(tc, fps=24)
        new_tc = timecode.timecode_from_frame(frame, fps=24)
        self.assertEqual(tc, new_tc)

        # try some drop frame versions of this
        df_tc = "02:03:04;05"
        frame = timecode.frame_from_timecode(df_tc, fps=29.97, drop=True)
        new_tc = timecode.timecode_from_frame(frame, fps=29.97, drop=True)
        self.assertEqual(df_tc, new_tc)
        frame = timecode.frame_from_timecode(df_tc, fps=59.94, drop=True)
        new_tc = timecode.timecode_from_frame(frame, fps=59.94, drop=True)
        self.assertEqual(df_tc, new_tc)

    def test_frame_round_trip(self):
        # We need to make sure frame values aren't mutated when going back and
        # forth from frames to tc to frames
        frames = [2394732, 12332, 8599999, 8640005]
        for frame in frames:
            tc = timecode.timecode_from_frame(frame, fps=24)
            new_frame = timecode.frame_from_timecode(tc, fps=24)
            self.assertEqual(frame, new_frame)

            # try some drop frame versions of this
            tc = timecode.timecode_from_frame(frame, fps=29.97, drop=True)
            new_frame = timecode.frame_from_timecode(tc, fps=29.97, drop=True)
            self.assertEqual(frame, new_frame)
            tc = timecode.timecode_from_frame(frame, fps=59.94, drop=True)
            new_frame = timecode.frame_from_timecode(tc, fps=59.94, drop=True)
            self.assertEqual(frame, new_frame)

    def test_fps_types(self):
        # Testing input of effective int and establishing the fact that these
        # are valid input types
        frame_rates = [24, 24.00, 60, 60.00]
        for fps in frame_rates:
            _int = int(fps)
            _float = float(fps)
            _decimal = decimal.Decimal(fps)
            frame = 2394732
            tc_int = timecode.timecode_from_frame(frame, fps=_int)
            tc_float = timecode.timecode_from_frame(frame, fps=_float)
            tc_decimal = timecode.timecode_from_frame(frame, fps=_decimal)
            self.assertEqual(tc_int, tc_float)
            self.assertEqual(tc_int, tc_decimal)
            self.assertEqual(tc_float, tc_decimal)
        # Testing input of non-int
        frame_rates = [23.976, 59.94]
        for fps in frame_rates:
            _float = float(fps)
            _decimal = decimal.Decimal(fps)
            frame = 2394732
            tc_float = timecode.timecode_from_frame(frame, fps=_float)
            tc_decimal = timecode.timecode_from_frame(frame, fps=_decimal)
            self.assertEqual(tc_float, tc_decimal)

    def test_unsupported_features(self):
        """
        Test unsupported features are correctly caught
        """
        path = os.path.join(self._unsupported_dir, "drop-frame.edl")
        # Check we get expected exception
        with self.assertRaises(BadDropFrameError):
            edl.EditList(file_path=path)
        path = os.path.join(self._unsupported_dir, "raphe_temp1_rfe_R01_v01.edl")
        with self.assertRaises(BadFrameRateError):
            edl.EditList(file_path=path)

    def test_frames_to_timecode(self):
        """
        Test we return the correct timecodes for various frame, fps, and drop frame settings.
        """
        for fps, drop, frame, expected_tc in self._frames_timecode_map:
            tc = timecode.timecode_from_frame(frame, fps=fps, drop=drop)
            self.assertEqual(str(tc), expected_tc)

    def test_timecode_to_frames(self):
        """
        Test we return the correct frames for various timecode, fps, and drop frame settings.
        """
        for fps, drop, expected_frame, tc in self._frames_timecode_map:
            frame = timecode.frame_from_timecode(tc, fps, drop)
            self.assertEqual(frame, expected_frame)
