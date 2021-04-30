# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import shutil
import os
import sys
from io import StringIO
import difflib
from ..dependencyfile import DependencyFile

TEST_PATH = "tests/test.xml"
TMP_PATH = "tests/test.xml.tmp"


# Test Fixtures and Helper Functions
@pytest.fixture
def xml_filepath():
    """
    Provides a filepath to a ivy.xml file for testing.
    This file is deleted after a test calling for this fixture terminates.

    :return: Path to a copy of the ivy.xml located at TEST_PATH
    """

    # Create the xml and pass the path to user
    shutil.copy(TEST_PATH, TMP_PATH)

    yield TMP_PATH
    # Delete the xml file
    os.remove(TMP_PATH)


@pytest.fixture
def df(xml_filepath):
    """
    Returns an unchanged DependencyFile object for testing.
    This DependencyFile object uses the xml from xml_filepath.

    :param xml_filepath: Copy of ivy.xml from xml_filepath()
    :return: DependencyFile object for passed in ivy.xml
    """
    return DependencyFile(xml_filepath)


def begin_capture():
    """
    Begins redirecting console output into a StringIO object.
    Useful for testing functions that print but don't return.

    :return: StringIO object tied to stdout (passed into retrieve_capture())
    """
    s = StringIO()
    sys.stdout = s
    return s


def retrieve_capture(s):
    """
    Stops redirecting stdout to the passed in StringIO object.

    :param s: StringIO object from begin_capture()
    :return: String containing all captured output since begin_capture() was called
    """

    sys.stdout = sys.__stdout__
    output = s.getvalue()
    s.close()
    return output


# Begin Tests
def test_init(df):
    """
    Ensures that DependencyFile initializes correctly.
    Checks member variables and ensures there are no crashes.

    :param df: DependencyFile object initialized with the ivy.xml at TEST_PATH
    :return:
    """
    assert df.path == TMP_PATH
    assert len(df.saved_changelog) == 0
    assert len(df.unsaved_changelog) == 0


def test_str(df):
    """
    Ensures that DependencyFile returns a string when printed.
    This string must contain info about dependencies in the file.

    :param df: DependencyFile object initialized with the ivy.xml at TEST_PATH
    :return:
    """
    s = DependencyFile.__str__(df)
    assert s != ""
    assert s is not None

    in_df = ["org.slf4j", "slf4j-log4j12", "1.7.30", "org.apache.commons", "commons-lang3", "3.11"]

    for word in in_df:
        assert word in s


def test_dependency_list(df):
    """
    Ensures that the dependency list returned has dependencies from the xml.

    :param df: DependencyFile object initialized with the ivy.xml at TEST_PATH
    :return:
    """
    assert len(df.dependency_list()) == 7
    for i in df.dependency_list():
        assert type(i) is dict

    # First dependency from xml as a dict
    expected_dict = {
        'org': 'org.slf4j',
        'name': 'slf4j-api',
        'rev': '1.7.30',
        'conf': '*->master'
    }
    assert df.dependency_list()[0] == expected_dict


def test_save(df):
    """
    Test saving without any changes to dependencies.
    No changes expected aside from minor differences in whitespace.

    :param df: DependencyFile object initialized with the ivy.xml at TEST_PATH
    :return:
    """

    # Save and read the 'unchanged' dependency file
    df.save()
    with open(TMP_PATH, "r") as f:
        modified_xml = f.readlines()
    with open(TEST_PATH, "r") as f:
        original_xml = f.readlines()

    # Generate and print diffs
    d = difflib.unified_diff(original_xml, modified_xml)
    print(''.join(d))

    # Assert that dependencies are not changed
    for i in d:
        if i[0] in ('+', '-'):
            assert 'dependency' not in i


def test_comments(df):
    """
    Ensures that various comments throughout the xml are preserved

    :param df: DependencyFile object initialized with the ivy.xml at TEST_PATH
    :return:
    """

    df.save()
    with open(TMP_PATH, "r") as f:
        modified_xml = f.readlines()

    # Check for all numbered comments in the saved xml
    for i in range(1, 6):
        found = False
        for line in modified_xml:
            if "Test comment " + str(i) in line:
                found = True
                break
        assert found

    # Check for multiline comment
    found = False
    for idx, line in enumerate(modified_xml):
        if "Test Multi" in line:
            found = True
            next_line = modified_xml[idx+1]
            assert "line comment 1" in next_line
            break
    assert found
