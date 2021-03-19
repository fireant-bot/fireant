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

from github import Github, InputGitAuthor, GithubException
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
        t = threading.Thread(target=run, name='th-' + str(i), kwargs={'dep_queue': dep_queue,
                                                                      'new_dep_queue': new_dep_queue})
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return new_dep_queue


def run(dep_queue, new_dep_queue):
    while not dep_queue.empty():
        dep = dep_queue.get()
        new_version = None
        attempts = config.HTTP_RETRY_ATTEMPTS
        while dep and 'org' in dep and 'name' in dep and not new_version and attempts > 0:
            try:
                new_version = newest_dependency_version(dep['org'], dep['name'])
            except IndexError:
                attempts -= 1

        if not new_version:
            continue

        dep['new_version'] = new_version
        new_dep_queue.put(dep)


def get_repo():
    repo_name = config.REPO_LINK.split('/')[-1]
    g = Github(config.GITHUB_USERNAME, config.GITHUB_PASSWORD)
    return g.get_user().get_repo(repo_name)


def get_open_pull_requests():
    pulls = get_repo().get_pulls(state='open')
    pages = int(pulls.totalCount / config.NUM_PULLS_PER_PAGE) + 1
    pull_arr = []
    for page in range(pages):
        pull_arr += pulls.get_page(page)[:]
    pull_title_dict = {}
    for pull in pull_arr:
        pull_title_dict.update({pull.title: 1})
    return pull_title_dict


def submit_upgrade_pull_request(name, old_version, new_version, branch):
    title = config.PULL_REQUEST_FORMAT.format(name, old_version, new_version)
    pr = get_repo().create_pull(title=title, body=title, head=branch, base="master")
    print('Created pull request: {}'.format(pr))


def main():
    dependencies = []

    print("Adding dependencies from ivy.xml")
    # Add all dependencies in main ivy file
    df = DependencyFile('{}/ivy/ivy.xml'.format(config.REPO_PATH))
    for dep in df.dependency_list():
        dependencies.append(dep)

    print("Adding dependencies from plugins")
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
            # print('Should update {} from version {} to version {}'.format(dep['name'], dep['rev'], dep['new_version']))

    print("Getting pull requests")

    # TODO: ALSO INCLUDE ivy/ivy.xml
    pull_title_dict = get_open_pull_requests()
    for plugin in os.listdir('{}'.format(repo_plugins_folder)):
        if os.path.isdir('{}/{}'.format(repo_plugins_folder, plugin)) and \
                os.path.exists('{}/{}/ivy.xml'.format(repo_plugins_folder, plugin)):

            file_path = '{}/{}/ivy.xml'.format(repo_plugins_folder, plugin)
            df = DependencyFile(file_path)

            for i, dep in enumerate(df.dependency_list()):
                # If no update needed
                if not dep or '{}-{}'.format(dep['org'], dep['name']) not in dep_dict:
                    continue

                old_version = dep_dict.get('{}-{}'.format(dep['org'], dep['name']))['rev']
                new_version = dep_dict.get('{}-{}'.format(dep['org'], dep['name']))['new_version']

                df.modify_version(i, new_version)
                df.save()

                title = config.PULL_REQUEST_FORMAT.format(dep['name'], old_version, new_version)
                if title not in pull_title_dict:
                    author = InputGitAuthor(
                        "fireant-ci",
                        "jaqwertyuiop12345@gmail.com"
                    )
                    branch_name = 'fireant_{}_{}'.format(dep['name'], new_version)
                    source = get_repo().get_branch(config.MAIN_BRANCH)
                    try:
                        get_repo().create_git_ref(ref='refs/heads/{}'.format(branch_name), sha=source.commit.sha)
                        git_path = '{}/{}/ivy.xml'.format(config.PLUGINS_FOLDER, plugin)[1:]
                        contents = get_repo().get_contents(git_path, ref=branch_name)
                        with open(file_path, 'r') as xml_file:
                            file_content = '\n'.join(xml_file.readlines())
                            get_repo().update_file(contents.path, title, file_content, contents.sha, branch=branch_name,
                                                   author=author)  # Commit and push update
                        submit_upgrade_pull_request(dep['name'], old_version, new_version, branch_name)
                    except GithubException:
                        pass

                df.modify_version(i, old_version)
                df.save()


if __name__ == '__main__':
    main()





