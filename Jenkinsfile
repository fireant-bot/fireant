pipeline {
    agent any
    environment {
        registry = 'mjemnawaz/newrepository'
        registryCredential = 'dockerHub_ID'
        dockerImage = ''
    }
    stages {
        stage('Checkout'){
            steps {
                checkout([$class: 'GitSCM', branches: [[name: '*/main']], extensions: [], userRemoteConfigs: [[url: 'https://github.com/fireant-ci/fireant.git']]])
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
        stage('Stop') {
            steps {
                sh 'docker ps -f name=fireant -q | xargs --no-run-if-empty docker container stop'
                sh 'docker container ls -a -fname=fireant -q | xargs -r docker container rm'
            }
        }
        stage('Run') {
            steps {
                script {
                    dockerImage.run("-p 8096:5000 --rm --name fireant")
                }
            }
        }
    }
}
