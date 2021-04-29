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

FROM python:3.9

WORKDIR /usr/src/app
ENV JAVA_HOME /usr/lib/jvm/java-11-openjdk-amd64
ENV ANT_HOME /usr/share/apache-ant

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install packages
RUN apt-get update \
 && apt-get -y --no-install-recommends install ant="1.10.5-2" openjdk-11-jdk="11.0.9.1+1-1~deb10u2" openjdk-11-jre="11.0.9.1+1-1~deb10u2"  openjdk-11-jre-headless="11.0.9.1+1-1~deb10u2" openjdk-11-jdk-headless="11.0.9.1+1-1~deb10u2" git="1:2.20.1-2+deb10u3" \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*


COPY . .

CMD [ "python", "./main.py"]
