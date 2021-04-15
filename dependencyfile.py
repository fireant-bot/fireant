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

from os import remove
from shutil import copyfile
import defusedxml.ElementTree as Et
import xml.sax.saxutils as saxutils


XML_LICENSE = """\n<!-- Licensed to the Apache Software Foundation (ASF) under one or more
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
-->\n\n"""


class DependencyFile:
    def __str__(self):
        res = []
        for item in self.__xml_tree.getroot().iter('dependency'):
            print(item.attrib)
            res.append(str(item.attrib) + '\n')
        return "".join(res)

    # Initialize class with a given filepath
    def __init__(self, path):
        self.path = path
        self.saved_changelog = []
        self.unsaved_changelog = []
        self.__dependency_list = []
        # Parse xml and preserve original comments
        self.__xml_tree = Et.parse(path,
                                   Et.XMLParser(
                                       target=Et._TreeBuilder(insert_comments=True),
                                       encoding="utf-8"))

        for count, item in enumerate(self.__xml_tree.getroot()):
            if item.tag != 'dependencies':
                continue
            self.__dependencies_index = count

            for dependency in item:
                self.__dependency_list.append(dependency.attrib)
        self.__backup = '/tmp/{}.bak'.format(hash(path))
        self.__save_backup()

    # Print log of all saved/unsaved changes
    def print_log(self):
        print("Changelog for dependency file:", self.path)
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

    # Return a list of all dependencies
    def dependency_list(self) -> list:
        return self.__dependency_list.copy()

    # Modify the 'rev' tag of a dependency
    # Accepts index of the dependency (from the list)
    # and the new version number
    def modify_version(self, index: int, version: str):
        xml_dependency = self.__xml_tree.getroot()[self.__dependencies_index][index]
        name = xml_dependency.attrib['name']
        old_version = xml_dependency.attrib['rev']

        # Change version
        xml_dependency.attrib['rev'] = version

        # Logging
        log_msg = "Update " + name + " " + old_version + " -> " + version
        self.unsaved_changelog.append(log_msg)

    # Removes a dependency
    def remove(self, index: int):
        xml_dependency = self.__xml_tree.getroot()[self.__dependencies_index]
        name = xml_dependency[index].attrib['name']
        old_version = xml_dependency[index].attrib['rev']
        xml_dependency.remove(xml_dependency[index])
        # Logging
        log_msg = "Remove " + name + " " + old_version
        self.unsaved_changelog.append(log_msg)

    def __write(self, path):
        # Write modified xml (non-escaped and missing header)
        self.__xml_tree.write(path, encoding="utf-8", method='xml', xml_declaration=True)

        f = open(path, "r")
        content = f.readlines()
        f.close()

        # Insert license and escape symbols
        content.insert(1, XML_LICENSE)
        content = "".join(content)
        content = saxutils.unescape(content)

        f = open(path, "w")
        f.write(content)
        f.close()

    # Save changes back to the original xml file
    # (path is only for debugging/testing purposes)
    def save(self, path=None):
        if path:
            self.__write(path)
        else:
            self.__write(self.path)

        # Logging
        self.saved_changelog.extend(self.unsaved_changelog)
        self.unsaved_changelog = []

    def __save_backup(self):
        copyfile(self.path, self.__backup)

    def close(self):
        remove(self.__backup)

    def revert_copy(self):
        copyfile(self.__backup, self.path)
        self.saved_changelog = []
        self.unsaved_changelog = []
        self.__dependency_list = []
        # Parse xml and preserve original comments
        self.__xml_tree = Et.parse(self.path,
                                 Et.XMLParser(
                                     target=Et._TreeBuilder(insert_comments=True),
                                     encoding="utf-8"))

        for count, item in enumerate(self.__xml_tree.getroot()):
            if item.tag != 'dependencies':
                continue
            self.__dependencies_index = count

            for dependency in item:
                self.__dependency_list.append(dependency.attrib)
