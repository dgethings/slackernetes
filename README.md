# Slackernetes

ChatOps bot for Devs to get info on their Kubernetes deployments.

## Installation

Use Helm.

```bash
helm install --name slackernetes helm/slackernetes --set-string bot_oauth_token <Slack API Bot User Token>
```

## Development Setup

To run Slackernetes in Minikube do the following.

```bash
eval $(minikube docker-env)
docker build --rm -f "Dockerfile" -t slackernetes:latest .
helm install --name slackernetes helm/slackernetes --set-string bot_oauth_token <Slack API Bot User Token> --set-string log_level=DEBUG
```
