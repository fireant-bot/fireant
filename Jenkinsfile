/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/* groovylint-disable CompileStatic, NestedBlockDepth */

pipeline {
    agent any
    environment {
        dockerImage = ''
        registry = 'fireantbot/fireant'
        registryCredential = 'FIREANT_DOCKERHUB_ID'
        slackChannel = '#jenkins'
        slackDomain = 'apachenutch401'
        slackMessage = 'Fireant Jenkins Pipeline - '
        slackToken = 'SLACK_TOKEN'
        slackUrl = 'https://hooks.slack.com/services/'
    }
    triggers {
        cron('0 0 * * *')
    }
    stages {
        stage('Checkout') {
            steps {
                checkout(
                    [$class: 'GitSCM',
                    branches: [[name: '*/main']],
                    extensions: [],
                    userRemoteConfigs: [[url: 'https://github.com/fireant-bot/fireant.git']]
                    ]
                )
            }
        }
        stage('Build') {
            steps {
                script {
                    dockerImage = docker.build registry
                }
            }
        }
        stage('Upload') {
            steps {
                script {
                    docker.withRegistry('', registryCredential) {
                        dockerImage.push()
                    }
                }
            }
        }
        stage('Run') {
            steps {
                script {
                    withCredentials(
                        [string(credentialsId: 'GITHUB_EMAIL', variable: 'EMAIL'),
                        string(credentialsId: 'GITHUB_PASSWORD', variable: 'PASS'),
                        string(credentialsId: 'GITHUB_USERNAME', variable: 'USER'),
                        string(credentialsId: 'REQUIRES_IO_TOKEN', variable: 'TOKEN')]
                        ) {
                        sh 'docker run -e GITHUB_USERNAME=$USER\
                            -e GITHUB_PASSWORD=$PASS\
                            -e GITHUB_EMAIL=$EMAIL\
                            -e REQUIRES_IO_TOKEN=$TOKEN fireantbot/fireant'
                    }
                }
            }
        }
    }
    post {
        success {
            slackSend baseUrl: slackUrl,
                channel: slackChannel,
                color: 'good',
                message: slackMessage + BUILD_NUMBER + ' - SUCCESS',
                teamDomain: slackDomain,
                tokenCredentialId: slackToken
        }
        failure {
            slackSend baseUrl: slackUrl,
                channel: slackChannel,
                color: '#FF0000',
                message: slackMessage + BUILD_NUMBER + ' - FAILURE',
                teamDomain: slackDomain,
                tokenCredentialId: slackToken
        }
    }
}
