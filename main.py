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


import glob
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

    # Ensure the version is stable (e.g., alpha or beta not in version)
    i = 0
    while any(char.isalpha() for char in resp['response']['docs'][i]['v']):
        i += 1
    version = resp['response']['docs'][i]['v']

    return version


def tag_new_dep_version(dependencies):
    dep_queue = Queue(config.MAXIMUM_DEPENDENCIES)
    new_dep_queue = Queue(config.MAXIMUM_DEPENDENCIES)
    for dep in dependencies:
        dep_queue.put(dep)

    threads = []
    for i in range(config.NETWORKING_THREADS_MAVEN):
        t = threading.Thread(target=tag_run, name='th-{}'.format(i), kwargs={'dep_queue': dep_queue,
                                                                             'new_dep_queue': new_dep_queue
                                                                             })
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return new_dep_queue


def tag_run(dep_queue, new_dep_queue):
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


def submit_upgrade_pull_request(name, path, new_version, branch):
    title = config.PULL_REQUEST_FORMAT.format(name, path, new_version)
    pr = get_repo().create_pull(title=title, body=title, head=branch, base="master")
    print('Created pull request: {}'.format(pr))


def get_dependencies():
    dependencies = []
    for dep_file in glob.glob('{}/**/ivy.xml'.format(config.REPO_PATH.replace('/', '')), recursive=True):
        df = DependencyFile(dep_file)
        for dep in df.dependency_list():
            dependencies.append(dep)

    return dependencies


def find_updated_dependency_versions(dependencies):
    dep_dict = {}
    dep_queue = tag_new_dep_version(dependencies)
    while not dep_queue.empty():
        dep = dep_queue.get()
        if dep['rev'] != dep['new_version']:
            dep_dict.update({'{}-{}'.format(dep['org'], dep['name']): dep})
            print('Should update {} from version {} to version {}'.format(dep['name'], dep['rev'], dep['new_version']))
    return dep_dict


def update_dependencies(dep_dict, open_pull_requests):
    file_queue = Queue(config.MAXIMUM_DEPENDENCIES)
    for dep_file in glob.glob('{}/**/ivy.xml'.format(config.REPO_PATH.replace('/', '')), recursive=True):
        file_queue.put(dep_file)

    threads = []
    for i in range(config.NETWORKING_THREADS_GITHUB):
        t = threading.Thread(target=update_run, name='th-{}'.format(i), kwargs={'file_queue': file_queue,
                                                                                'dep_dict': dep_dict,
                                                                                'open_pull_requests': open_pull_requests
                                                                                })
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def update_run(file_queue, dep_dict, open_pull_requests):
    while not file_queue.empty():
        file_path = file_queue.get()
        df = DependencyFile(file_path)
        for i, dep in enumerate(df.dependency_list()):
            # If no update needed
            if not dep or '{}-{}'.format(dep['org'], dep['name']) not in dep_dict:
                continue

            old_version = dep_dict.get('{}-{}'.format(dep['org'], dep['name']))['rev']
            new_version = dep_dict.get('{}-{}'.format(dep['org'], dep['name']))['new_version']

            df.modify_version(i, new_version)
            df.save()

            title = config.PULL_REQUEST_FORMAT.format(dep['name'], file_path, new_version)
            if title not in open_pull_requests:
                author = InputGitAuthor(
                    config.GITHUB_USERNAME,
                    config.GITHUB_EMAIL
                )
                branch_name = 'fireant_{}_{}'.format(dep['name'], new_version)
                source = get_repo().get_branch(config.MAIN_BRANCH)
                try:
                    print('Submitting pull request: {}'.format(title))
                    get_repo().create_git_ref(ref='refs/heads/{}'.format(branch_name), sha=source.commit.sha)
                    strip_from = len(config.REPO_PATH.replace('/', '') + '/')
                    git_path = file_path[strip_from:]
                    contents = get_repo().get_contents(git_path, ref=branch_name)
                    with open(file_path, 'r') as xml_file:
                        file_content = ''.join(xml_file.readlines())
                        get_repo().update_file(contents.path, title, file_content, contents.sha, branch=branch_name,
                                               author=author)  # Commit and push update
                    submit_upgrade_pull_request(dep['name'], file_path, new_version, branch_name)
                except GithubException as e:
                    print(e)

            df.modify_version(i, old_version)
            df.save()


def main():
    # Pull dependencies from local repo
    print("\n\nPulling dependencies from local repo")
    print('*********************************************************************************************')
    dependencies = get_dependencies()

    # Tag the dependencies with new versions pulled from Maven
    print("\n\nPulling new dependency versions from maven")
    print('*********************************************************************************************')
    dependency_dict = find_updated_dependency_versions(dependencies)

    # Get current open pull requests
    print("\n\nGetting all current pull requests")
    print('*********************************************************************************************')
    open_pull_requests = get_open_pull_requests()

    # Submit pull requests for all dependencies that must be updated
    # but that do not currently have a corresponding pull request
    print("\n\nSubmitting pull request updates")
    print('*********************************************************************************************')
    update_dependencies(dependency_dict, open_pull_requests)


if __name__ == '__main__':
    setup_env()
    main()





