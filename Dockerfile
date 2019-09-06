FROM python:3-alpine

WORKDIR /app
ENTRYPOINT [ "./slack_bot.py" ]

# Or your actual UID, GID on Linux if not the default 1000
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

COPY requirements.txt /tmp/pip-tmp/

RUN pip --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp
    #
    # Create a non-root user to use if preferred - see https://aka.ms/vscode-remote/containers/non-root-user.
    # && groupadd --gid $USER_GID $USERNAME \
    # && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME

COPY slackernetes.py slack_bot.py /app
