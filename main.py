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
import threading
from queue import Queue
import os

from github import Github
import urllib3

import config
from dependencyfile import DependencyFile


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


def newest_dependency_version(org, name):
    http = urllib3.PoolManager()
    resp = http.request('GET', config.MAVEN_SEARCH_URL.format(org, name))

    if resp.status != 200:
        raise urllib3.exceptions.ConnectionError

    resp = json.loads(resp.data)
    i = 0
    while any(char.isalpha() for char in resp['response']['docs'][i]['v']):
        i += 1
    version = resp['response']['docs'][i]['v']
    return version


def tag_new_dep_version(dependencies):
    dep_queue = Queue(1000)
    new_dep_queue = Queue(1000)
    for dep in dependencies:
        dep_queue.put(dep)

    threads = []
    for i in range(8):
        t = threading.Thread(target=run, name='th-' + str(i), kwargs={'dep_queue': dep_queue, 'new_dep_queue': new_dep_queue})
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return new_dep_queue


def run(dep_queue, new_dep_queue):
    while not dep_queue.empty():
        dep = dep_queue.get()
        # TODO: EXCEPTION HANDLING BECAUSE THIS FUNCTION WILL THROW EXCEPTION !!! especially networking
        try:
            new_version = newest_dependency_version(dep['org'], dep['name'])
        except KeyError:  # Dict empty
            continue
        dep['new_version'] = new_version
        new_dep_queue.put(dep)


def submit_upgrade_pull_request(file, name, old_version, new_version):
    pass


def main():
    dependencies = []

    # Add all dependencies in main ivy file
    df = DependencyFile('{}/ivy/ivy.xml'.format(config.REPO_PATH))
    for dep in df.dependency_list():
        dependencies.append(dep)

    # Add all dependencies from plugins
    repo_plugins_folder = config.REPO_PATH + config.PLUGINS_FOLDER
    for plugin in os.listdir('{}'.format(repo_plugins_folder)):
        if os.path.isdir('{}/{}'.format(repo_plugins_folder, plugin)) and \
                os.path.exists('{}/{}/ivy.xml'.format(repo_plugins_folder, plugin)):
            df = DependencyFile('{}/{}/ivy.xml'.format(repo_plugins_folder, plugin))
            for dep in df.dependency_list():
                dependencies.append(dep)

    # Convert queue to dict
    dep_dict = {}
    dep_queue = tag_new_dep_version(dependencies)
    while not dep_queue.empty():
        dep = dep_queue.get()
        if dep['rev'] != dep['new_version']:
            dep_dict.update({'{}-{}'.format(dep['org'], dep['name']): dep})
            print('Should update {} from version {} to version {}'.format(dep['name'], dep['rev'], dep['new_version']))

    for plugin in os.listdir('{}'.format(repo_plugins_folder)):
        if os.path.isdir('{}/{}'.format(repo_plugins_folder, plugin)) and \
                os.path.exists('{}/{}/ivy.xml'.format(repo_plugins_folder, plugin)):
            df = DependencyFile('{}/{}/ivy.xml'.format(repo_plugins_folder, plugin))
            for i, dep in enumerate(df.dependency_list()):
                # If no update needed
                if '{}-{}'.format(dep['org'], dep['name']) not in dep_dict:
                    continue
                old_version = dep_dict.get('{}-{}'.format(dep['org'], dep['name']))['rev']
                new_version = dep_dict.get('{}-{}'.format(dep['org'], dep['name']))['new_version']
                df.modify_version(0, new_version)
                df.save()

                # TODO: CHECK IF THERE ISN'T ALREADY A PULL REQUEST FOR THAT VERSION UPGRADE
                # TODO: SEND PULL REQUEST IF ABOVE CONDITION MET

                df.modify_version(0, old_version)
                df.save()


if __name__ == '__main__':
    main()

