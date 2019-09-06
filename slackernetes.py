#!/usr/bin/env python3
import os
import slack
import logging
import kubernetes
import re
import time
import atexit

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

# kubernetes.config.load_kube_config(config_file="kube_config")
kubernetes.config.load_incluster_config()
k = kubernetes.client.CoreV1Api()

COMMANDS = dict()

MY_ID = ""

def register(regex):
    """
    Decorator to register function as a supported command
    """
    def decorator_register(func):
        global COMMANDS
        COMMANDS[regex] = func
    return decorator_register

@register(r"(?:get|list) images in namespace (\S+)")
def list_images(**payload):
    """
    List images used in a namespace
    """
    namespace = re.search(payload['regex'], payload['data']['text']).group(1)
    payload['web_client'].chat_postMessage(
        channel=payload['data']['channel'],
        text=f"Here are all the images in `{namespace}` I can find:\n" + "\n".join([ container.image for pod in k.list_namespaced_pod(namespace).items for container in pod.spec.containers ])
    )

@register(r"(help|(list|get) commands?)")
def show_help(**payload):
    """
    List all available commands
    """
    cmds = [ f"{regex}    {func.__doc__}" for regex, func in COMMANDS.items() ]
    payload['web_client'].chat_postMessage(
        channel=payload['data']['channel'],
        text="Here are all the supported commands:\n" + "\n".join(cmds)
    )


@register(r"(?:get|list) pods? in namespace (\S+)$")
def list_pods(**payload):
    """
    List all the Pods in a namespace
    """
    namespace = re.search(payload['regex'], payload['data']['text']).group(1)
    payload['web_client'].chat_postMessage(
        channel=payload['data']['channel'],
        text=f"Here are all the pods in `{namespace}` I can find:\n" + "\n".join([ pod.metadata.name for pod in k.list_namespaced_pod(namespace).items ])
    )

@register(r"(?:get|list) pods?$")
def list_all_pods(**payload):
    """
    List all the Pods in a cluster
    """
    pod_list = [ pod.metadata.name for pod in k.list_pod_for_all_namespaces(watch=False).items ]
    payload['web_client'].chat_postMessage(
        channel=payload['data']['channel'],
        text="Here are all the pods I can find:\n" + "\n".join(pod_list)
    )

@register(r"(?:get|list) logs? for pod (\S+)$")
def pod_logs(**payload):
    """
    Get logs for a given pod
    """
    pod_name = re.search(payload['regex'], payload['data']['text']).group(1)
    pod = next (( pod for pod in k.list_pod_for_all_namespaces(watch=False).items if pod_name in pod.metadata.name), None)
    logging.debug(f"found this pod: {pod}")
    payload['web_client'].files_upload(
        channels=payload['data']['channel'],
        initial_comment=f"Here are the logs from `{pod_name}`",
        content=k.read_namespaced_pod_log(pod_name, pod.metadata.namespace)
    )

@register(r"(?:get|list) previous logs? for pod (\S+)$")
def pod_logs(**payload):
    """
    Get logs for a previous instance of a given pod
    """
    pod_name = re.search(payload['regex'], payload['data']['text']).group(1)
    pod = next (( pod for pod in k.list_pod_for_all_namespaces(watch=False).items if pod_name in pod.metadata.name), None)
    logging.debug(f"found this pod: {pod}")
    payload['web_client'].files_upload(
        channels=payload['data']['channel'],
        initial_comment=f"Here are the logs from `{pod_name}`",
        content=k.read_namespaced_pod_log(pod_name, pod.metadata.namespace, previous=True)
    )

@register(r"(get|list) namespaces$")
def list_namespaces(**payload):
    """
    List all namespaces in a cluster.
    """
    ns_list = [ ns.metadata.name for ns in k.list_namespace().items ]
    payload['web_client'].chat_postMessage(
        channel=payload['data']['channel'],
        text="Here are all the namespaces I can find:\n" + "\n".join(ns_list)
    )

@register(r"describe pod (.+)")
def describe_pod(**payload):
    """
    Get details about a pod include env vars and other useful info
    """
    pod_name = re.search(payload['regex'], payload['data']['text']).group(1)
    pod = next (( pod for pod in k.list_pod_for_all_namespaces(watch=False).items if pod_name in pod.metadata.name), None)
    logging.debug(f"found this pod: {pod}")
    payload['web_client'].files_upload(
        channels=payload['data']['channel'],
        initial_comment=f"Here is the description for pod {pod_name}",
        content=k.read_namespaced_pod(pod_name, pod.metadata.namespace, pretty="true")
    )

def unsupported_command(**payload):
    """
    Gracefully handle unknown commands
    """
    logging.debug(f"the message text not currently handled: {payload['data']['text']}")
    payload['web_client'].chat_postMessage(
        channel=payload['data']['channel'],
        text=f"Sorry, I don't understand: {payload['data']['text']}"
    )

def for_bot(message):
    global MY_ID
    if re.search(r"^<@" + re.escape(MY_ID) + r">.+", message.get('text')):
        return True
    else:
        return False

@slack.RTMClient.run_on(event="open")
def get_my_id(**payload):
    """
    Gets the ID for this bot user. It is used to determine which nessages the bot should respond to.
    """
    global MY_ID
    if payload['data']['ok']:
        MY_ID = payload['data']['self']['id']

    logging.debug(f"My ID is: {MY_ID}")

@slack.RTMClient.run_on(event="message")
def handle_message(**payload):
    message = payload['data']
    if not for_bot(message): return
    # all other types of submessages
    if message.get('subtype'):
        logging.debug(f"currently don't handle subtype {message['subtype']}")
        return

    (regex, func) = next( ( (cmd, COMMANDS[cmd]) for cmd in COMMANDS if re.search(cmd, message['text'] ) ), (r".*", unsupported_command))
    log_request(payload, func)
    payload['regex'] = regex
    func(**payload)

def log_request(payload, func):
    web_client = payload['web_client']
    username = web_client.users_info(user=payload['data']['user'])
    channel = web_client.channels_info(channel=payload['data']['channel'])
    message = re.search(r"^<@" + re.escape(MY_ID) + r"> (.*)", payload['data']['text']).group(1)
    logging.info(f"slackernetes_request{{username=\"{username['user']['name']}\",function_name=\"{func.__name__}\",channel=\"{channel.data['channel']['name']}\",message=\"{message}\"}} 1 {time.time()}")

@atexit.register
def log_app_stop():
    logging.info(f'slackernetes_status{{state="stop"}} 1 {time.time()}')

if __name__ == "__main__":
    slack_token = os.environ["SLACK_API_TOKEN"]
    rtm_client = slack.RTMClient(token=slack_token)
    logging.info(f'slackernetes_status{{state="start"}} 1 {time.time()}')
    rtm_client.start()
