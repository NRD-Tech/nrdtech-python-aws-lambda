# Python AWS Lambda App
This is a project template for a python application that will be triggered either by an Event Bridge schedule, an SQS queue, or an API Gateway endpoint

# Technology Stack
* Python 3.12
* Docker
* Terraform

# Setting Up Your Development Environment

## Clone and Clean the template (if using GitHub)
* Navigate to: https://github.com/NRD-Tech/nrdtech-python-aws-lambda.git
* Log into your GitHub account (otherwise the "Use this template" option will not show up)
* Click "Use this template" in the top right corner
  * Create a new repository
* Fill in your repository name, description, and public/private setting
* Clone your newly created repository
* If you want to change the license to be proprietary follow these instructions: [Go to Proprietary Licensing Section](#how-to-use-this-template-for-a-proprietary-project)

## Clone and Clean the template (if NOT using GitHub)
```
git clone https://github.com/NRD-Tech/nrdtech-python-aws-lambda.git my-project
cd my-project
rm -fR .git venv .idea
git init
git add .
git commit -m 'init'
```
* If you want to change the license to be proprietary follow these instructions: [Go to Proprietary Licensing Section](#how-to-use-this-template-for-a-proprietary-project)

## Dev Environment Pre-Requisites
1. Make sure Python 3.12 and Poetry are installed on your computer
```
# Mac Terminal
# Install brew if you haven't already
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python@3.12 poetry
```
```
# Windows PowerShell (run as an Administrator)
# Install choco if you haven't already
# https://chocolatey.org/install

# Install Python 3.12
choco install python --version=3.12 -y

# Install Poetry globally
$env:POETRY_HOME = "C:\Program Files\Poetry"
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Put Poetry and Python in the PATH
[System.Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\Poetry\bin", [System.EnvironmentVariableTarget]::Machine)

# NOTE: You will need to open a new terminal after adding Poetry and Python to your PATH for it to take effect
```
2. Tell poetry to create virtual environments in the project folder
```
poetry config virtualenvs.in-project true
```

## VSCode Setup
1. Open the folder containing the project
2. Run the following in the terminal to set up the virtual environment
```
# Assure the use of python3.12
poetry env use python3.12

# Set up the virtual environment and installs dependencies
poetry install

# Verify Python Version in Use
poetry env info
```
3. Configure the Python Interpreter
* Mac: Command-Shift-P -> Python: Select Interpreter
* Windows: Control-Shift-P -> Python: Select Interpreter
* Choose the Python in .venv/bin/python


## PyCharm Setup
1. Open the folder containing the project
2. PyCharm should automatically detect the poetry project and offer to create the virtual environment - Click "OK"
  * If it doesn't, go to Settings -> Project -> Project Interpreter
  * Click Add Interpreter -> Add Local Interpreter
  * Configure:
    * Engironment: Generate new
    * Type: Poetry
    * Base python: <path to your python 3.12>
    * Path to poetry: <path to poetry>
  * Click OK
  * Note: Sometimes I need to restart PyCharm after this for it to recognize the new interpereter correctly
3. Go to PyCharm Settings -> Project -> Project Structure
  * Mark the app folder as "Sources"
  * Mark the tests folder as "Tests"
  * Click "OK"
4. Run the following in the terminal
```
# Set up the virtual environment and installs dependencies
poetry install

# Verify Python Version in Use
poetry env info
```

At this point you should have a fully working local development environment.  The steps below this are setting up to be able to deploy the project to AWS.
---

# Configuring the App for AWS Deployment

## OIDC Pre-Requisite
* You must have previously set up the AWS Role for OIDC and S3 bucket for the Terraform state files
* The easiest way to do this is to use the NRD-Tech Terraform Bootstrap template
  * https://github.com/NRD-Tech/nrdtech-terraform-aws-account-bootstrap
  * After following the README.md instructions in the bootstrap template project you should have:
    * An AWS Role ARN
    * An AWS S3 bucket for the Terraform state files

## Configure Settings
* Edit .env.global
  * Each config is a little different per application but at a minimum you will need to change:
    * APP_IDENT_WITHOUT_ENV
    * TERRAFORM_STATE_BUCKET
    * AWS_DEFAULT_REGION
    * AWS_ROLE_ARN
* Choose how your lambda function will be triggered and un-comment the appropriate terraform:
  * Event Bridge Scheduling:
    * Un-comment terraform/main/lambda_eventbridge_schedule.tf
    * Set the schedule that you want as a cron or rate in terraform/main/lambda_eventbridge_schedule.tf
    * Edit lambda_handler.py to enable the appropriate section
  * SQS Triggered:
    * Un-comment terraform/main/lambda_sqs_trigger.tf
    * Edit lambda_handler.py to enable the appropriate section
  * API Gateway:
    * Un-comment terraform/main/lambda_api_gateway.tf
    * Edit lambda_handler.py to enable the appropriate section
    * Configure the domain's in .env.prod and .env.staging
* Commit your changes to git
```
git add .
git commit -a -m 'updated config'
```

## (If using Bitbucket) Enable Bitbucket Pipeline (NOTE: GitHub does not require any setup like this for the Actions to work)
* Push your git project up into a new Bitbucket project
* Navigate to your project on Bitbucket
  * Click Repository Settings
  * Click Pipelines->Settings
    * Click Enable Pipelines

## (If using GitHub) Configure the AWS Role
* Edit .github/workflows/main.yml
  * Set the pipeline role for role-to-assume
  * Set the correct aws-region

## Deploy to Staging
```
git checkout -b staging
git push --set-upstream origin staging
```

## Deploy to Production
```
git checkout -b production
git push --set-upstream origin production
```

## Un-Deploying in Bitbucket
1. Navigate to the Bitbucket project website
2. Click Pipelines in the left nav menu
3. Click Run pipeline button
4. Choose the branch you want to un-deploy
5. Choose the appropriate un-deploy Pipeline
   * un-deploy-staging
   * un-deploy-production
6. Click Run

# Poetry Cheat Sheet
| **Action**                   | **Command**                                                                                  |
|-------------------------------|----------------------------------------------------------------------------------------------|
| **Install Poetry**            | `curl -sSL https://install.python-poetry.org | python3 -`                                   |
|                               | `export PATH="$HOME/.local/bin:$PATH"`                                                      |
|                               | `poetry --version`                                                                          |
| **Initialize Project**        | New Project: `poetry new my_project`                                                        |
|                               | Existing Project: `poetry init`                                                             |
| **Add Dependencies**          | Regular: `poetry add requests`                                                              |
|                               | Dev-only: `poetry add --dev pytest`                                                         |
|                               | Specific Version: `poetry add flask@2.3.2`                                                 |
|                               | From Git: `poetry add git+https://github.com/user/repo.git`                                  |
|                               | With Extras: `poetry add pandas[all]`                                                      |
| **Install Dependencies**      | `poetry install`                                                                            |
| **Virtual Environment**       | Activate: `poetry shell`                                                                    |
|                               | Run w/o Activate: `poetry run python script.py`                                             |
|                               | Deactivate: `exit`                                                                          |
| **Update Dependencies**       | Update All: `poetry update`                                                                 |
|                               | Update Specific: `poetry update requests`                                                  |
| **Remove Dependencies**       | `poetry remove requests`                                                                    |
| **Lock File**                 | Regenerate: `poetry lock`                                                                   |
| **Export Dependencies**       | `poetry export -f requirements.txt --output requirements.txt`                               |
| **Check for Updates**         | `poetry show --outdated`                                                                    |
| **Build & Publish**           | Build: `poetry build`                                                                       |
|                               | Publish: `poetry publish --username <username> --password <password>`                       |
| **Configure Poetry**          | Show Config: `poetry config --list`                                                        |
|                               | Venv in Project: `poetry config virtualenvs.in-project true`                                |
|                               | Unset Config: `poetry config --unset <key>`                                                |

# Misc How-To's

## How to use this template for a proprietary project
This project's license (MIT License) allows for you to create proprietary code based on this template.

Here are the steps to correctly do this:
1. Replace the LICENSE file with your proprietary license terms if you wish to use your own license.
2. Optionally, include a NOTICE file stating that the original work is licensed under the MIT License and specify the parts of the project that are governed by your proprietary license.

## How to set up to use CodeArtifact dependencies

### One Time: setup of pyproject.tml to access the CodeArtifact dependencies
```
# Get the Repo Endpoint and add it to your pyproject.toml
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCOUNT_ID=1234567890
export CODEARTIFACT_DOMAIN=mycompanydomain
export CODEARTIFACT_REPOSITORY=mycompany-py-repo
export AWS_PROFILE=mycompany_aws_profile

export CODEARTIFACT_URL=$(aws --region $AWS_DEFAULT_REGION codeartifact get-repository-endpoint --domain $CODEARTIFACT_DOMAIN --domain-owner $AWS_ACCOUNT_ID --repository $CODEARTIFACT_REPOSITORY --format pypi --query repositoryEndpoint --output text)
poetry source add $CODEARTIFACT_DOMAIN $CODEARTIFACT_URL"simple" --priority=supplemental
```

### Each Day: Authenticate with CodeArtifact to access the private dependencies
```
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCOUNT_ID=1234567890
export CODEARTIFACT_DOMAIN=mycompanydomain
export AWS_PROFILE=mycompany_aws_profile

export CODEARTIFACT_TOKEN=$(aws --region $AWS_DEFAULT_REGION codeartifact get-authorization-token --domain $CODEARTIFACT_DOMAIN --domain-owner $AWS_ACCOUNT_ID --query authorizationToken --output text)
poetry config http-basic.$CODEARTIFACT_DOMAIN aws $CODEARTIFACT_TOKEN
```

## How To run docker image locally
```
aws ecr get-login-password \
      --region us-west-2 | \
      docker login \
        --username AWS \
        --password-stdin 1234567890.dkr.ecr.us-west-2.amazonaws.com/myapp_lambda_repository

docker run --rm -p 9000:8080 -it 482370276428.dkr.ecr.us-west-2.amazonaws.com/myapp_lambda_repository:latest 

curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'

```

# How To Inspect docker image
```
alias dive="docker run -ti --rm  -v /var/run/docker.sock:/var/run/docker.sock wagoodman/dive"
dive 1234567890.dkr.ecr.us-west-2.amazonaws.com/myapp_lambda_repository:latest
```

# How to view the architecture (and other info) of a docker image
```
export AWS_PROFILE=mycompanyprofile
docker logout 1234567890.dkr.ecr.us-west-2.amazonaws.com
aws ecr get-login-password \
      --region us-west-2 | \
      docker login \
        --username AWS \
        --password-stdin 1234567890.dkr.ecr.us-west-2.amazonaws.com/myapp_lambda_repository
docker pull 1234567890.dkr.ecr.us-west-2.amazonaws.com/myapp_lambda_repository
docker inspect 1234567890.dkr.ecr.us-west-2.amazonaws.com/myapp_lambda_repository
```
