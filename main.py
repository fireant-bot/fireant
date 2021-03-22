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

#!/usr/bin/python3

import subprocess
import os
import config
from dependencyfile import DependencyFile

from github import Github


def debug():
    print("Testing python docker image")
    subprocess.run(['java', '-version'])
    subprocess.run(['git', 'version'])
    subprocess.run(['ant', '-version'])
    print("Testing env variables")
    print('JAVA_HOME:', os.environ['JAVA_HOME'])
    print('ANT_HOME:', os.environ['ANT_HOME'])
    subprocess.run(['ant'], cwd=config.REPO_PATH)


def setup_env():
    REPO_LINK = config.REPO_LINK
    REPO_PATH = config.REPO_PATH

    if not os.path.isdir(REPO_PATH):
        subprocess.run(['git', 'clone', REPO_LINK, REPO_PATH])


def main():
    # TODO dynamically get a list of all ivy.xml files
    for c, f in enumerate(config.IVY_FILE_LIST):
        df = DependencyFile(config.REPO_PATH + "/" + f)
        # Update logic should go here
        df.modify_version(0, "5.3.7")
        df.print_log()
        df.save(str(c) + '_example.xml')
        df.print_log()
        print()


if __name__ == '__main__':
    setup_env()
    main()

