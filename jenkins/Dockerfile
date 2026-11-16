# Jenkins with Terraform, Python and the plugins the pipeline needs, configured as code.
FROM jenkins/jenkins:lts-jdk17

USER root
ARG TERRAFORM_VERSION=1.14.5
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl unzip python3 python3-venv python3-pip \
 && curl -fsSL -o /tmp/tf.zip https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
 && unzip /tmp/tf.zip -d /usr/local/bin \
 && rm -rf /tmp/tf.zip /var/lib/apt/lists/*
USER jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

COPY casc.yaml /usr/share/jenkins/casc.yaml
ENV CASC_JENKINS_CONFIG=/usr/share/jenkins/casc.yaml \
    JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
