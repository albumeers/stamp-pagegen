pipeline {
    agent any

    triggers {
        cron('H/15 * * * *')
    }

    tools {
        maven 'MAVEN'   // Name of Maven installation configured in Jenkins global tools
    }

    stages {
        stage('Checkout') {
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/master']],
                    userRemoteConfigs: [[
                        url: 'https://github.com/albumeers/stamp-pagegen.git',
                        credentialsId: 'jadrake-github'
                    ]]
                ])
            }
        }

        stage('Build') {
            steps {
                sh 'mvn clean package -DskipTests'
            }
        }
    }

    post {
        success {
            archiveArtifacts artifacts: 'target/stamp-pagegen*', fingerprint: true
        }
        failure {
            echo 'Build failed'
        }
    }
}