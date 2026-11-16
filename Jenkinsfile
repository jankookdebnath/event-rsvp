// One click ("Build Now") -> pull code from GitHub -> run tests -> Terraform provisions EC2
// -> the server builds and runs the Docker container -> pipeline waits until the app is live.
pipeline {
    agent any

    parameters {
        choice(name: 'ACTION', choices: ['deploy', 'destroy'],
               description: 'deploy = create/update the app on AWS, destroy = delete everything it created')
    }

    environment {
        AWS_ACCESS_KEY_ID     = credentials('aws-access-key-id')
        AWS_SECRET_ACCESS_KEY = credentials('aws-secret-access-key')
        AWS_DEFAULT_REGION    = 'ap-south-1'
        TF_IN_AUTOMATION      = 'true'
        TF_STATE              = '/var/jenkins_home/tfstate/event-rsvp.tfstate'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
    }

    stages {
        stage('Checkout from GitHub') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT_FULL = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
                    env.REPO_URL = sh(script: 'git config --get remote.origin.url', returnStdout: true).trim()
                }
                echo "Deploying ${env.REPO_URL} @ ${env.GIT_COMMIT_FULL}"
            }
        }

        stage('Unit tests') {
            when { expression { params.ACTION != 'destroy' } }
            steps {
                dir('app') {
                    sh '''
                        python3 -m venv .venv
                        . .venv/bin/activate
                        pip install -q -r requirements.txt
                        pytest -q
                    '''
                }
            }
        }

        stage('Terraform init') {
            steps {
                dir('terraform') {
                    sh 'mkdir -p "$(dirname "$TF_STATE")"'
                    sh 'terraform init -input=false -reconfigure -backend-config="path=$TF_STATE"'
                }
            }
        }

        stage('Terraform plan') {
            when { expression { params.ACTION != 'destroy' } }
            steps {
                dir('terraform') {
                    sh '''
                        terraform validate
                        terraform plan -input=false -out=tfplan \
                          -var "repo_url=$REPO_URL" -var "git_commit=$GIT_COMMIT_FULL"
                    '''
                }
            }
        }

        stage('Provision infrastructure') {
            when { expression { params.ACTION != 'destroy' } }
            steps {
                dir('terraform') {
                    sh 'terraform apply -input=false -auto-approve tfplan'
                    script {
                        env.APP_URL = sh(script: 'terraform output -raw app_url', returnStdout: true).trim()
                    }
                }
            }
        }

        stage('Wait for app to go live') {
            when { expression { params.ACTION != 'destroy' } }
            steps {
                // First boot installs Docker and builds the image, which takes a few minutes.
                sh '''
                    for i in $(seq 1 60); do
                      if curl -fsS --max-time 5 "$APP_URL/health"; then
                        echo; echo "App is live at $APP_URL"; exit 0
                      fi
                      echo "Waiting for app ($i/60)..."; sleep 10
                    done
                    echo "App did not become healthy in 10 minutes"; exit 1
                '''
            }
        }

        stage('Destroy infrastructure') {
            when { expression { params.ACTION == 'destroy' } }
            steps {
                dir('terraform') {
                    sh 'terraform destroy -input=false -auto-approve -var "repo_url=$REPO_URL"'
                }
            }
        }
    }

    post {
        success {
            script {
                if (params.ACTION != 'destroy') {
                    currentBuild.description = "Live: ${env.APP_URL}"
                    echo "SUCCESS - open ${env.APP_URL}"
                } else {
                    currentBuild.description = 'Infrastructure destroyed'
                }
            }
        }
    }
}
