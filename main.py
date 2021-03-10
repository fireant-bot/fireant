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

import json
import subprocess
import os

from github import Github
import urllib3

import config


def setup_env():
    REPO_LINK = config.REPO_LINK
    # consider changing this to an absolute path
    REPO_PATH = '.repo'

    print("Testing python docker image")
    subprocess.run(['java', '-version'])
    subprocess.run(['git', 'version'])
    subprocess.run(['ant', '-version'])
    print("Testing env variables")
    print('JAVA_HOME:', os.environ['JAVA_HOME'])
    print('ANT_HOME:', os.environ['ANT_HOME'])
    if not os.path.isdir(REPO_PATH):
        subprocess.run(['git', 'clone', REPO_LINK, REPO_PATH])
    subprocess.run(['ant'], cwd=REPO_PATH)


def newest_dependency_version(org, name):
    http = urllib3.PoolManager()
    resp = http.request('GET', config.MAVEN_SEARCH_URL.format(org, name))

    if resp.status != 200:
        raise urllib3.exceptions.ConnectionError

    resp = json.loads(resp.data)
    version = resp['response']['docs'][0]['v']

    return version


def change_dependency_version(file, name, version):
    pass


def submit_upgrade_pull_request(file, name, old_version, new_version):
    pass


def main():
    repo_name = config.REPO_LINK.split('/')[-1].split('.')[0]
    deps_to_update = []
    for plugin in os.listdir('{}/src/plugin/'.format(repo_name)):
        if os.path.isdir('{}/src/plugin/{}'.format(repo_name, plugin)) and \
                os.path.exists('{}/src/plugin/{}/ivy.xml'.format(repo_name, plugin)):
            # ADD OUTDATED DEPENDENCIES (AND THE FILES THEY'RE LOCATED IN) TO deps_to_update
            print('Found plugin: {}'.format(plugin))
            # print(newest_dependency_version('org.apache.commons', 'commons-rdf-api'))

    for dependency in deps_to_update:
        change_dependency_version(dependency['file'], dependency['name'], dependency['new_version'])
        submit_upgrade_pull_request(dependency['file'], dependency['name'],
                                    dependency['old_version'], dependency['new_version'])
        change_dependency_version(dependency['file'], dependency['name'], dependency['old_version'])


if __name__ == '__main__':
    # setup_env()
    main()

