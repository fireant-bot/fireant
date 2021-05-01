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
        registry = 'fireantbot/fireant'
        registryCredential = 'FIREANT_DOCKERHUB_ID'
        dockerImage = ''
    }
    triggers {
        cron('0 0 * * *')
        GenericTrigger(
            tokenCredentialId: 'FIREANT_WEBHOOK'
        )
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
                    withCredentials([string(credentialsId: 'GITHUB_EMAIL', variable: 'GITHUB_EMAIL'), string(credentialsId: 'GITHUB_PASSWORD', variable: 'GITHUB_PASSWORD'), string(credentialsId: 'GITHUB_USERNAME', variable: 'GITHUB_USERNAME'), string(credentialsId: 'REQUIRES_IO_TOKEN', variable: 'REQUIRES_IO_TOKEN')]) {
                         sh 'docker run -e GITHUB_USERNAME=$GITHUB_USERNAME -e GITHUB_PASSWORD=$GITHUB_PASSWORD -e GITHUB_EMAIL=$GITHUB_EMAIL -e REQUIRES_IO_TOKEN=$REQUIRES_IO_TOKEN fireantbot/fireant'
                    }
                }
            }
        }
    }
    post {
        success {
            slackSend baseUrl: 'https://hooks.slack.com/services/',
                channel: '#jenkins',
                color: 'good',
                message: 'Fireant Jenkins Pipeline - ' + BUILD_NUMBER + ' - SUCCESS',
                teamDomain: 'apachenutch401',
                tokenCredentialId: 'SLACK_TOKEN'
        }
        failure {
             slackSend baseUrl: 'https://hooks.slack.com/services/',
                channel: '#jenkins',
                color: '#FF0000',
                message: 'Fireant Jenkins Pipeline - ' + BUILD_NUMBER + ' - FAILURE',
                teamDomain: 'apachenutch401',
                tokenCredentialId: 'SLACK_TOKEN'
        }
    }
}
