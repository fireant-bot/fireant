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
import os
import subprocess
import threading
from queue import Queue
from shutil import Error as ShutilError
from shutil import which

import urllib3
from github import Github, InputGitAuthor, GithubException, Repository

import config
from dependencyfile import IvyDependencyFile, write_plugin_library_updates


def debug() -> bool:
    """
    :return: boolean indicating whether or not system has necessary software installed and set up
    """
    print("Testing python docker image")
    try:
        subprocess.run(['{}'.format(which('java')), '-version'], check=True)
        subprocess.run(['{}'.format(which('git')), 'version'], check=True)
        subprocess.run(['{}'.format(which('ant')), '-version'], check=True)
    except subprocess.CalledProcessError:
        print("Java, Git, or Ant is not installed.")
        return False
    except ShutilError:
        print("Error reading which ant, git, or java is being used by system")
        return False
    print("Testing env variables")
    print('JAVA_HOME:', os.environ['JAVA_HOME'])
    print('ANT_HOME:', os.environ['ANT_HOME'])
    try:
        subprocess.run(['{}'.format(which('ant'))], cwd=config.REPO_PATH, check=True)
    except subprocess.CalledProcessError:
        print("Ant build failed to run")
        return False
    except ShutilError:
        print("Error reading which ant is being used by system")
        return False
    return True


def setup_env() -> bool:
    """
    Attempts to synchronize the local, forked, and remote repositories

    :return: boolean indicating whether or not forked repo is up to date with the remote repo
    """
    REPO_LINK = config.FORKED_LINK
    REPO_PATH = config.REPO_PATH
    if not os.path.isdir(REPO_PATH):
        try:
            subprocess.run(['{}'.format(which('git')), 'clone', REPO_LINK, REPO_PATH], check=True)
        except subprocess.CalledProcessError:
            print("Cloning repo {} to {} was not successful".format(REPO_LINK, REPO_PATH))
            return False
        except ShutilError:
            print("Error reading which git is being used by system")
            return False
    else:
        try:
            update_forked_repo()
            subprocess.run(['{}'.format(which('git')), '-C', REPO_PATH, 'pull'], check=True)
        except subprocess.CalledProcessError:
            print("Pulling repo failed")
            return False
        except ShutilError:
            print("Error reading which git is being used by system")
            return False
    return True


def update_forked_repo() -> bool:
    """
    Attempts to merge the forked repository with the upstream remote repository

    :return: boolean indicating whether or not the forked repository has been merged with the remote repository
    """
    remote_org = config.REMOTE_REPO_LINK.split('/')[-2]
    forked_org = config.FORKED_LINK.split('/')[-2]
    branch = config.MAIN_BRANCH
    merge_message = "merge {0}:{2} with {1}:{2}".format(forked_org,remote_org, branch)
    try:
        pull = get_forked_repo().create_pull(title=merge_message, body=merge_message,
                                             head='{}:{}'.format(remote_org, branch), base=branch,
                                             maintainer_can_modify=True)
        pull.merge(merge_message)
        return True
    except GithubException as e:
        print("Duplicate pull request, repo up-to-date, or merge failed: {}".format(e))
        return False


def newest_dependency_version(org: str, name: str, rev: str) -> str:
    """
    Pulls and returns the latest stable version of the dependency specified by the parameters

    :param org: the name of the organization that created the dependency (i.e., "org.apache.commons")
    :param name: the name of the dependency itself, used in Maven (i.e., "commons-lang3")
    :param rev: the dependency version, this is used to determine if a newer dependency is available
    :return: string representing the latest stable version of the dependency (i.e., "3.11")
    """
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
    # Ensure the fetched dependency is greater than the one we had
    if version < rev:
        return rev
    return version


def tag_new_dep_version(dependencies: []) -> Queue:
    """
    Tags all provided dependencies with an additional attribute specifying their latest stable version

    :param dependencies: a list of dependencies (a dict of attributes that specify a dependency)
    :return: queue.Queue object containing all provided dependencies with an additional attribute tag ('new_version')
            that specifies the latest version of the dependency
    """
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


def tag_run(dep_queue: Queue, new_dep_queue: Queue):
    """
    Loops through all dependencies in the dependency queue, tags them with their latest stable version, and inserts
     them in a new input queue.

    :param dep_queue: a queue with a number of dependencies in it
    :param new_dep_queue: an empty queue that will be filled with the original dependencies and an additional tag
    """
    while not dep_queue.empty():
        dep = dep_queue.get()
        new_version = None
        attempts = config.HTTP_RETRY_ATTEMPTS
        while dep and 'org' in dep and 'name' in dep and not new_version and attempts > 0:
            try:
                new_version = newest_dependency_version(dep['org'], dep['name'], dep['rev'])
            except IndexError:
                attempts -= 1
        if not new_version:
            continue
        dep['new_version'] = new_version
        new_dep_queue.put(dep)


def get_forked_repo() -> Repository:
    """
    :return: a github.Repository object allowing interaction with the forked repository
    """
    repo_name = config.FORKED_LINK.split('/')[-1]
    g = Github(config.GITHUB_USERNAME, config.GITHUB_PASSWORD)
    return g.get_user().get_repo(repo_name)


def get_remote_repo() -> Repository:
    """
    :return: a github.Repository object allowing interaction with the remote repository
    """
    repo_name = config.REMOTE_REPO_LINK.split('/')[-1]
    org = config.REMOTE_REPO_LINK.split('/')[-2]
    g = Github(config.GITHUB_USERNAME, config.GITHUB_PASSWORD)
    return g.get_repo('{}/{}'.format(org, repo_name))


def get_open_pull_requests() -> dict:
    """
    :return: a dictionary (set) of titles of all open pull requests in the forked repository
    """
    pulls = get_forked_repo().get_pulls(state='open')
    pages = int(pulls.totalCount / config.NUM_PULLS_PER_PAGE) + 1
    pull_arr = []
    for page in range(pages):
        pull_arr += pulls.get_page(page)[:]
    pull_title_dict = {}
    for pull in pull_arr:
        pull_title_dict.update({pull.title: 1})
    return pull_title_dict


def submit_upgrade_pull_request(name: str, path: str, new_version: str, old_version: str, branch: str,
                                duplicate: bool = False):
    """
    Attempts to submit a pull request to the remote repository using a branch from the forked repository

    :param name: the name of the dependency being changed by the commit
    :param path: the git path of the file being changed by the commit
    :param old_version: the string representation of the old/previous version of the dependency being changed
    :param new_version: the string representation of the new version of the dependency being changed
    :param branch: the name of the branch in the forked repository used for the pull request
    :param duplicate: indicates whether or not there were duplicate dependencies deleted in the commit
    """
    title = config.PULL_REQUEST_FORMAT.format(name, path, old_version, new_version)
    org = config.FORKED_LINK.split('/')[-2]
    if duplicate:
        title += config.DUPLICATE_MESSAGE
    pr = get_remote_repo().create_pull(title=title, body=title, head='{}:{}'.format(org, branch),
                                       base=config.MAIN_BRANCH)
    print('Created pull request: {}'.format(pr))


def get_dependencies() -> []:
    """
    :return: returns a list of all dependencies used in the repository via all files called ivy.xml
    """
    dependencies = []
    for ivy_file in glob.glob('{}/**/ivy.xml'.format(config.REPO_PATH.replace('/', '')), recursive=True):
        idf = IvyDependencyFile(ivy_file)
        for ivy_dep in idf.dependency_list():
            dependencies.append(ivy_dep)
    return dependencies


def find_updated_dependency_versions(dependencies: []) -> dict:
    """
    Maps dependency identifiers to the the dependency tagged with the new version and filters up-to-date dependencies

    :param dependencies: a list of dependencies (a dictionary of attributes of the dependency)
    :return: a dictionary mapping dependency identifiers with the associated dependency with an additional version tag
    """
    dep_dict = {}
    dep_queue = tag_new_dep_version(dependencies)
    while not dep_queue.empty():
        dep = dep_queue.get()
        if dep['rev'] != dep['new_version']:
            dep_dict.update({'{}-{}'.format(dep['org'], dep['name']): dep})
            print('Should update {} from version {} to version {}'.format(dep['name'], dep['rev'], dep['new_version']))
    return dep_dict


def is_dependency_valid(dep: dict, dep_dict: dict) -> bool:
    """
    :param dep: a dependency that may or may not be valid or up-to-date
    :param dep_dict: a dictionary mapping dependency identifiers to their up-to-date dependency counterparts
    :return: a boolean indicating whether the dependency is out-of-date or not
    """
    if not dep or 'org' not in dep or 'name' not in dep or '{}-{}'.format(dep['org'], dep['name']) not in dep_dict:
        return False
    return True


def update_dependencies(dep_dict: dict, open_pull_requests: dict):
    """
     Attempts to upgrade all outdated dependencies in the repository and submit pull requests containing updates
    to the dependencies to the upstream remote repository

    :param dep_dict: a dictionary mapping dependency identifiers to their up-to-date dependency counterparts
    :param open_pull_requests: a dictionary (set) of all open pull request titles in the forked repository
    """
    file_queue = Queue(config.MAXIMUM_DEPENDENCIES)
    for dep_file in glob.glob('{}/**/ivy.xml'.format(config.REPO_PATH.replace('/', '')), recursive=True):
        file_queue.put(dep_file)
    threads = []
    for i in range(config.NETWORKING_THREADS_GITHUB):
        t = threading.Thread(
            target=update_run, name='th-{}'.format(i),
            kwargs={'file_queue': file_queue, 'dep_dict': dep_dict, 'open_pull_requests': open_pull_requests})
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def process_plugin_xml(ivy_file_path: str):
    """
    Executes the necessary steps to complete a dependency update by updating the plugin.xml
    file (assuming it is a plugin being updated). This is documented in steps 3 and 5 from
    https://github.com/apache/nutch/blob/master/src/plugin/parse-tika/howto_upgrade_tika.txt
    :param ivy_file_path: the path on disk to the plugin.xml for the plugin being updated
    """
    if ivy_file_path != '.repo/ivy/ivy.xml':
        plugin_dir = ivy_file_path.replace('ivy.xml', '')
        # Ignore certain plugins which do not have build-ivy.xml files
        if 'build-ivy.xml' in os.listdir(plugin_dir):
            plugin_file = ivy_file_path.replace('ivy.xml', 'plugin.xml')
            subprocess.run(['{}'.format(which('ant')), "-f", "./build-ivy.xml"],
                           cwd=plugin_dir, check=True, capture_output=True)
            str_cmd = "{} {} | {} 's/^/      <library name=\"/g' | {} 's/$/\"\/>/g'" # skipcq: PYL-W1401
            cmd = str_cmd.format(which('ls'), './lib', which('sed'), which('sed'))
            plugin_libs = subprocess.run(
                [cmd], capture_output=True, check=True, cwd=plugin_dir, shell=True) # skipcq: BAN-B602
            write_plugin_library_updates(plugin_file, plugin_libs.stdout.decode('utf-8'))


def update_run(file_queue: Queue, dep_dict: dict, open_pull_requests: dict):
    """
    Loops through all ivy.xml files in the repository and attempts to update all outdated dependencies in the file and
    submit pull requests containing updates to the dependencies to the upstream remote repository

    :param file_queue: a queue containing all ivy.xml files in the repository
    :param dep_dict:a dictionary mapping dependency identifiers to their up-to-date dependency counterparts
    :param open_pull_requests: a dictionary (set) of all open pull request titles in the forked repository
    """
    while not file_queue.empty():
        ivy_file_path = file_queue.get()
        df = IvyDependencyFile(ivy_file_path)
        deps = {}
        for i, dep in enumerate(df.dependency_list()):
            # If invalid entry; also check for duplicates earlier in file
            if not is_dependency_valid(dep, dep_dict) or '{}-{}'.format(dep['org'], dep['name']) in deps:
                continue
            # Check for duplicates later in file
            remove = []
            for j, dupe_dep in enumerate(df.dependency_list()[i+1:]):
                if not is_dependency_valid(dupe_dep, dep_dict):
                    continue
                if dep['org'] == dupe_dep['org'] and dep['name'] == dupe_dep['name']:
                    print('Removing duplicate: {} - {} in {}'.format(dep['org'], dep['name'], ivy_file_path))
                    remove.append(j)
            # Remove duplicates
            for j, dupe_dep_num in enumerate(remove):
                df.remove(dupe_dep_num-j+i+1)
            deps.update({'{}-{}'.format(dep['org'], dep['name']): 1})
            new_version = dep_dict.get('{}-{}'.format(dep['org'], dep['name']))['new_version']
            old_version = dep['rev']
            df.modify_version(i, new_version)
            df.save()
            process_plugin_xml(ivy_file_path)
            strip_from = len(config.REPO_PATH.replace('/', '') + '/')
            git_path = ivy_file_path[strip_from:]
            title = config.PULL_REQUEST_FORMAT.format(dep['name'], git_path, old_version, new_version)
            from jira_utils import create_nutch_jira_issue
            nutch_jira_title = create_nutch_jira_issue(title=title)
            title = '[{}] {}'.format(nutch_jira_title, title)
            if title not in open_pull_requests:
                author = InputGitAuthor(
                    config.GITHUB_USERNAME,
                    config.GITHUB_EMAIL
                )
                branch_name = 'fireant_{}_{}'.format(dep['name'], new_version)
                source = get_forked_repo().get_branch(config.MAIN_BRANCH)
                try:
                    print('Submitting pull request: {}'.format(title))
                    # Create branch
                    get_forked_repo().create_git_ref(ref='refs/heads/{}'.format(branch_name), sha=source.commit.sha)

                    # Commit updates to ivy.xml on new branch
                    ivy_contents = get_forked_repo().get_contents(git_path, ref=branch_name)
                    with open(ivy_file_path, 'r') as ivy_xml_file:
                        ivy_file_content = ''.join(ivy_xml_file.readlines())
                    # Commit and push update to new branch
                    get_forked_repo().update_file(ivy_contents.path, title, ivy_file_content, ivy_contents.sha,
                                                  branch=branch_name, author=author)

                    # Commit updates to plugin.xml on new branch
                    plugin_contents = get_forked_repo().get_contents(git_path.replace('ivy', 'plugin'), ref=branch_name)
                    with open(ivy_file_path.replace('ivy', 'plugin'), 'r') as plugin_xml_file:
                        plugin_file_content = ''.join(plugin_xml_file.readlines())
                    # Commit and push update to new branch
                    get_forked_repo().update_file(plugin_contents.path, title, plugin_file_content, plugin_contents.sha,
                                                  branch=branch_name, author=author)

                    submit_upgrade_pull_request(
                        dep['name'], git_path, new_version, old_version, branch_name, len(remove) > 0)
                except GithubException as e:
                    print(e)
            df.revert_copy()
        df.close()


def main():
    # Pull dependencies from local repo
    print("\n\nPulling dependencies from local repo")
    print('*********************************************************************************************')
    dependencies = get_dependencies()
    # Tag the dependencies with new versions pulled from Maven
    print("\n\nPulling new dependency versions from Maven Central")
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
    if setup_env():
        main()
    else:
        print("Setup was not successful.")
