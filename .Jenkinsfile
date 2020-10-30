pipeline {
    agent {
        docker {
            image 'ubuntu_tester'
            args '-u root:root -v ${HOME}/html/docs:/docs -v ${HOME}/html/_ci:/ci'
        }
    }
    environment {
        PJ_NAME = 'fitlog'
        POST_URL = 'https://open.feishu.cn/open-apis/bot/v2/hook/ab4aa33b-1c7a-403c-8a83-fdc27fc9d8d1'
    }
    stages {
        stage('Package Installation') {
            steps {
                sh 'python setup.py install'
            }
        }
        stage('Parallel Stages') {
            parallel {
                stage('Document Building') {
                    steps {
                        sh 'cd docs && make prod'
                        sh 'rm -rf /docs/${PJ_NAME}'
                        sh 'mv docs/build/html /docs/${PJ_NAME}'
                    }
                }
                stage('Package Testing') {
                    steps {
                        sh 'pytest ./test --html=test_results.html --self-contained-html'
                    }
                }
            }
        }
    }
    post {
        always {
            sh 'post'
        }

    }

}
