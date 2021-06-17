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

import config
from jira import JIRA


def create_nutch_jira_issue(title: str):
    jira = JIRA(server="https://issues.apache.org/jira", basic_auth=(config.JIRA_USERNAME, config.JIRA_PASSWORD))
    return jira.create_issue(fields={'components': [{'name': 'build'}, {'name': 'fireant'}], 'description': title,
                              'fixVersions': [{'name': config.NEXT_NUTCH_RELEASE}], 'issuetype': 'Improvement',
                              'project': 'NUTCH', 'summary': title
                              }
                      )
