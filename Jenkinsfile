pipeline {
    agent any

    triggers {
        githubPush()
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
                        credentialsId: 'github'
                    ]]
                ])
            }
        }

        stage('Clean') {
            steps {
                sh 'mvn clean'
            }
        }
        
        stage('Build') {
            steps {
                sh 'mvn compile'
            }
        }
        
        stage('Test') {
            steps {
                sh 'mvn test -Dbuild.number=${BUILD_NUMBER}'
            }
        }

        stage('Python Test') {
            steps {
                sh '''
                    mkdir -p target/python-reports
                    if command -v pytest >/dev/null 2>&1; then
                        pytest build-tools/tests src/test/python --junitxml=target/python-reports/python-test-results.xml
                    else
                        python -m unittest discover -s build-tools/tests -p "test_*.py"
                        python -m unittest discover -s src/test/python -p "test_*.py"
                    fi
                '''
            }
        }
        
        stage('Package') {
            steps {
                sh 'mvn package -DskipTests -Dbuild.number=${BUILD_NUMBER}'
            }
        }
    }

    post {
        always {
        	junit allowEmptyResults: true, testResults: 'target/surefire-reports/*.xml,target/python-reports/*.xml,web-app/test/junit/*.xml'
    	}
        success {
            archiveArtifacts artifacts: 'target/stamp-pagegen*', fingerprint: true
        }
        failure {
            echo 'Build failed'
        }
    }
}