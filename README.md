# Event RSVP: one-click deployment to AWS

A small dynamic web app where you create events and people RSVP **Yes / Maybe / No**.
One click in Jenkins pulls the code from GitHub, tests it, provisions AWS infrastructure
with Terraform, and deploys the app in Docker on EC2.

## Tech stack

| Requirement | Used for |
|---|---|
| **AWS Cloud** | EC2 (t3.micro, Amazon Linux 2023) + Security Group in `ap-south-1` |
| **Git / GitHub** | Source code; Jenkins checks out the repo, EC2 clones the same commit |
| **Jenkins** | Pipeline (`Jenkinsfile`), runs in Docker on the laptop, configured as code |
| **Terraform** | Provisions the security group and EC2 instance (`terraform/`) |
| **Docker** | App image built and run on EC2; Jenkins itself also runs in Docker |
| App | Python Flask + SQLite (dynamic: create events, RSVP, live counts) |

## The one-click flow

```
Build Now (Jenkins)
  -> Checkout from GitHub
  -> Unit tests (pytest)
  -> terraform init / plan
  -> terraform apply      (Security Group + EC2 created on AWS)
  -> EC2 boot script: install Docker, git clone, docker build, docker run
  -> Jenkins polls /health until the app is live and prints the URL
```

Pushing a new commit and clicking **Build Now** again replaces the server with the new version,
because the commit ID is part of the EC2 user data. Run the job with `ACTION=destroy` to delete
everything on AWS.

## Project layout

```
app/                 Flask app, templates, tests, Dockerfile
terraform/           main.tf, variables.tf, outputs.tf, user_data.sh.tpl
Jenkinsfile          the pipeline
jenkins/             Jenkins image (Terraform + plugins), casc.yaml, docker-compose.yml
```

## Setup (once)

1. Create an IAM user with an access key that can manage EC2 (e.g. `AmazonEC2FullAccess`).
2. `cd jenkins`, copy `.env.example` to `.env`, fill in the AWS keys and the GitHub repo URL.
3. `docker compose up -d --build`, then open http://localhost:8080 and log in with the admin from `.env`.
4. Open the **event-rsvp-deploy** job and click **Build Now** (first run: *Build with Parameters* → `deploy`).

## Run the app locally

```
cd app
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
pytest -q
```

## Notes

- Data is stored in SQLite in a Docker volume on the EC2 instance; a redeploy creates a new
  instance, so data starts fresh after each deployment.
- Remember to run the job with `ACTION=destroy` after the demo to avoid AWS charges.
