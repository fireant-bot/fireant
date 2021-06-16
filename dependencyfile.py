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

import xml.etree.ElementTree as ET  # Not using this module in an unsafe way -- skipcq: BAN-B405
import xml.sax.saxutils as saxutils
from os import remove
from shutil import copyfile

from defusedxml.ElementTree import parse, XMLParser

import config

XML_LICENSE = """<!-- 
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
-->\n"""


class IvyDependencyFile:
    def __str__(self):
        """
        Returns a string with all dependencies in the xml.

        :return: string containing dependency information
        """
        res = []
        for item in self.__xml_tree.getroot().iter('dependency'):
            res.append(str(item.attrib) + '\n')
        return "".join(res)

    def __init__(self, path):
        """
        Construct a new IvyDependencyFile object for a given ivy.xml file.

        :param path: filepath to ivy.xml to be modified
        """
        self.path = path
        self.saved_changelog = []
        self.unsaved_changelog = []
        self.__dependency_list = []
        # Parse xml and preserve original comments
        self.__xml_tree = parse(self.path, XMLParser(target=ET.TreeBuilder(insert_comments=True), encoding='utf-8'))

        # Iterate through all dependencies and place their information into a list
        for count, item in enumerate(self.__xml_tree.getroot()):
            if item.tag != 'dependencies':
                continue
            self.__dependencies_index = count

            for dependency in item:
                self.__dependency_list.append(dependency.attrib)

        # Temporarily backup the original ivy.xml while this IvyDependencyFile is being used/modified
        self.__backup = '{}/{}.bak'.format(config.TMP_DIRECTORY, hash(path))
        self.__save_backup()

    def print_log(self):
        """
        Prints all modifications made to the IvyDependencyFile.
        Unsaved changes have not been written back to the ivy.xml,
        while saved changes have.

        :return:
        """
        print("Changelog for ivy dependency file:", self.path)
        if not self.saved_changelog and not self.unsaved_changelog:
            print("No logged changes")
        if self.saved_changelog:
            print("--- Saved changes ---")
            for i in self.saved_changelog:
                print(i)
        if self.unsaved_changelog:
            print("--- Unsaved changes ---")
            for i in self.unsaved_changelog:
                print(i)

    def dependency_list(self) -> list:
        """
        Returns a list of all dependencies found in the ivy.xml.
        The indexes of each dependency in this list are used for
        removing and updating their versions.

        :return: list of dicts with information for each dependency
        """
        return self.__dependency_list.copy()

    def modify_version(self, index: int, version: str):
        """
        Modifies the version of a single dependency in the ivy.xml.
        This directly modifies the 'rev' tag in the xml.

        :param index: index of dependency to modify (from dependency_list)
        :param version: new version for updated dependency
        :return:
        """
        xml_dependency = self.__xml_tree.getroot()[self.__dependencies_index][index]
        name = xml_dependency.attrib['name']
        old_version = xml_dependency.attrib['rev']

        # Change version
        xml_dependency.attrib['rev'] = version

        # Logging
        log_msg = "Update " + name + " " + old_version + " -> " + version
        self.unsaved_changelog.append(log_msg)

    def remove(self, index: int):
        """
        Removes a dependency from the ivy.xml.

        :param index: index of dependency to remove from the ivy.xml
        :return:
        """
        xml_dependency = self.__xml_tree.getroot()[self.__dependencies_index]
        name = xml_dependency[index].attrib['name']
        old_version = xml_dependency[index].attrib['rev']
        xml_dependency.remove(xml_dependency[index])
        # Logging
        log_msg = "Remove " + name + " " + old_version
        self.unsaved_changelog.append(log_msg)

    def __write(self, path):
        """
        Internal function for writing the contents of
        this IvyDependencyFile (including modifications)
        to the given filepath. Also inserts Apache
        License and escapes symbols.

        :param path: filepath where modified xml will be written
        :return:
        """
        # Write modified xml (non-escaped and missing header)
        self.__xml_tree.write(path, encoding="utf-8", method='xml', xml_declaration=True)

        with open(path, "r") as f:
            content = f.readlines()

        # Insert license and escape symbols
        content.insert(1, XML_LICENSE)
        content = "".join(content)
        content = saxutils.unescape(content)

        with open(path, "w") as f:
            f.write(content)

    def save(self, path=None):
        """
        Save and write all changes back to the originally
        provided ivy.xml (or to a specific filepath).
        All unsaved changes will now be shown as saved
        when the log is printed.

        :param path: filepath where xml will be written (optional)
        :return:
        """
        if path:
            self.__write(path)
        else:
            self.__write(self.path)

        # Logging
        self.saved_changelog.extend(self.unsaved_changelog)
        self.unsaved_changelog = []

    def __save_backup(self):
        """
        Copy original ivy.xml to backup path.

        :return:
        """
        copyfile(self.path, self.__backup)

    def close(self):
        """
        Call when finished using this IvyDependencyFile.
        Deletes the temporary backup.

        :return:
        """
        remove(self.__backup)

    def revert_copy(self):
        """
        Reset IvyDependencyFile to its original state
        from the backup (before modifications).

        :return:
        """
        copyfile(self.__backup, self.path)
        self.saved_changelog = []
        self.unsaved_changelog = []
        self.__dependency_list = []
        # Parse xml and preserve original comments
        self.__xml_tree = parse(self.path, XMLParser(target=ET.TreeBuilder(insert_comments=True), encoding='utf-8'))

        for count, item in enumerate(self.__xml_tree.getroot()):
            if item.tag != 'dependencies':
                continue
            self.__dependencies_index = count

            for dependency in item:
                self.__dependency_list.append(dependency.attrib)


def write_plugin_library_updates(plugin_file_path: str, library_updates: str):
    # Parse xml and preserve original comments
    xml_tree = parse(plugin_file_path, XMLParser(target=ET.TreeBuilder(insert_comments=True), encoding='utf-8'))

    # Iterate through all libraries and place their information into a list
    root = xml_tree.getroot()
    runtime = root.find("./runtime")
    for library in root.findall("./runtime/library")[1:]:
        runtime.remove(library)
    for library_element in library_updates.split('\n')[:-1]:
        ET.SubElement(runtime, 'library', attrib={'name': library_element.split('"')[1]})

    ET.indent(xml_tree, space='  ')
    xml_tree.write(plugin_file_path, encoding="utf-8", method='xml', xml_declaration=True)
    with open(plugin_file_path, "r") as f:
        content = f.readlines()

    # Insert license and escape symbols
    content.insert(1, XML_LICENSE)
    content = "".join(content)
    content = saxutils.unescape(content)

    with open(plugin_file_path, "w") as f:
        f.write(content)
