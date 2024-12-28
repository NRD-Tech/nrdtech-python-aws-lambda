# Python AWS Lambda App
This is a project template for a python application that will be triggered either by an Event Bridge schedule, an SQS queue, or an API Gateway endpoint

# Technology Stack
* Python 3.12
* Docker
* Terraform

# Using this Template

## Clone and Clean the template (if using GitHub)
* Navigate to: https://github.com/NRD-Tech/nrdtech-python-aws-lambda.git
* Click "Use this template" in the top right corner
  * Create a new repository
* Fill in your repository name, description, and public/private setting
* Clone your newly created repository
* Update the License to 

## Clone and Clean the template (if NOT using GitHub)
```
git clone https://github.com/NRD-Tech/nrdtech-python-aws-lambda.git my-project
cd my-project
rm -fR .git venv .idea
git init
git add .
git commit -m 'init'
```

## Dev Environment Pre-Requisites
Make sure Python 3.12 and Poetry are installed on your computer
```
# Mac
brew install python@3.12
brew install poetry

# Windows
choco install python --version=3.12 -y
choco install poetry -y
```

## VSCode Setup
1. Open the folder containing the project
2. Run the following in the terminal to set up the virtual environment
```
# Set up the virtual environment in the project folder
poetry config virtualenvs.in-project true

# Assure the use of python3.12
poetry env use python3.12

# Set up the virtual environment and installs dependencies
poetry install

# Verify Python Version in Use
poetry env info
```

### PyCharm Setup
1. Open the folder containing the project
2. PyCharm should automatically detect the poetry project and offer to create the virtual environment - accept this option

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
    * SNS_TOPIC_FOR_ALARMS
      * Make sure to choose an SNS Topic that already exists and will notify your dev team of problems
* Choose how your lambda function will be triggered and un-comment the appropriate terraform:
  * Event Bridge Scheduling:
    * Un-comment terraform/main/lambda_eventbridge_schedule.tf
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
This project's license (Apache License 2.0) allows for you to create proprietary code based on this template.

Here are the steps to correctly do this:
1. Keep the original LICENSE file
2. Create a new file called LICENSE_PROPRIETARY that includes your proprietary license terms
3. Create a NOTICE file that contains something like this:

| Portions of this project are based on a template licensed under the Apache License 2.0. These portions are © NRD Tech LLC.
All other modifications, additions, and new work are © [Your Name or Your Company] and are governed by a proprietary license as described in LICENSE_PROPRIETARY.

## How to set up to use CodeArtifact dependencies

### One Time: setup of pyproject.tml to access the CodeArtifact dependencies
```
# Get the Repo Endpoint and add it to your pyproject.toml
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCOUNT_ID=1234567890
export CODEARTIFACT_DOMAIN=mycompanydomain
export CODEARTIFACT_REPOSITORY=mycompany-py-repo

export CODEARTIFACT_URL=$(AWS_PROFILE=mycompany_aws_profile aws --region $AWS_DEFAULT_REGION codeartifact get-repository-endpoint --domain $CODEARTIFACT_DOMAIN --domain-owner $AWS_ACCOUNT_ID --repository $CODEARTIFACT_REPOSITORY --format pypi --query repositoryEndpoint --output text)
poetry source add $CODEARTIFACT_DOMAIN $CODEARTIFACT_URL"simple" --priority=supplemental
```

### Each Day: Authenticate with CodeArtifact to access the private dependencies
```
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCOUNT_ID=1234567890
export CODEARTIFACT_DOMAIN=mycompanydomain

export CODEARTIFACT_TOKEN=$(AWS_PROFILE=mycompany_aws_profile aws --region $AWS_DEFAULT_REGION codeartifact get-authorization-token --domain $CODEARTIFACT_DOMAIN --domain-owner $AWS_ACCOUNT_ID --query authorizationToken --output text)
poetry config http-basic.$CODEARTIFACT_DOMAIN aws $CODEARTIFACT_TOKEN
```

## How To run docker image locally
```
aws ecr get-login-password \
      --region us-west-2 | \
      docker login \
        --username AWS \
        --password-stdin 482370276428.dkr.ecr.us-west-2.amazonaws.com/myapp_lambda_repository

docker run --rm -p 9000:8080 -it 482370276428.dkr.ecr.us-west-2.amazonaws.com/myapp_lambda_repository:latest 

curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'

```

# How To Inspect docker image
```
alias dive="docker run -ti --rm  -v /var/run/docker.sock:/var/run/docker.sock wagoodman/dive"
dive 482370276428.dkr.ecr.us-west-2.amazonaws.com/myapp_lambda_repository:latest
```
