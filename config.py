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

import os

# Fireant settings
NETWORKING_THREADS_MAVEN = 8
NETWORKING_THREADS_GITHUB = 1
MAXIMUM_DEPENDENCIES = 1000
TMP_DIRECTORY = "/tmp"

# GitHub settings
REMOTE_REPO_LINK = "https://github.com/apache/nutch"
FORKED_LINK = "https://github.com/fireant-ci/nutch"
REPO_PATH = ".repo"
PLUGINS_FOLDER = "/src/plugin"
NUM_PULLS_PER_PAGE = 25
PULL_REQUEST_FORMAT = "fireant upgrade dependency {} in {} from {} to {}"
DUPLICATE_MESSAGE = " and duplicate dependency deleted"
MAIN_BRANCH = "master"

# Maven search settings
MAVEN_SEARCH_URL = "https://search.maven.org/solrsearch/select?q=g:{}%20AND%20a:{}&core=gav&start=0&rows=20"
HTTP_RETRY_ATTEMPTS = 3

# NUTCH settings
NEXT_NUTCH_RELEASE = '1.19'

# Sensitive settings
try:
    GITHUB_USERNAME = os.environ['GITHUB_USERNAME']
    GITHUB_PASSWORD = os.environ['GITHUB_PASSWORD']
    GITHUB_EMAIL = os.environ['GITHUB_EMAIL']
    REQUIRES_IO_TOKEN = os.environ['REQUIRES_IO_TOKEN']
    JIRA_USERNAME = os.environ['JIRA_USERNAME']
    JIRA_PASSWORD = os.environ['JIRA_PASSWORD']
except KeyError as e:
    print(e)
    print("Could not get environment variables for GitHub settings or Requires.io")
