#!/usr/bin/env python3
from slackernetes import k, send_file, send_message, register, run
import logging
import re


@register(r"(?:get|list) images in namespace (\S+)")
def list_images(**payload):
    """
    List images used in a namespace
    """
    namespace = re.search(payload["regex"], payload["data"]["text"]).group(1)
    message = f"Here are all the images in `{namespace}` I can find:\n" + "\n".join(
        [
            container.image
            for pod in k.list_namespaced_pod(namespace).items
            for container in pod.spec.containers
        ]
    )
    send_message(message, payload)


@register(r"(?:get|list) pods? in namespace (\S+)$")
def list_pods(**payload):
    """
    List all the Pods in a namespace
    """
    namespace = re.search(payload["regex"], payload["data"]["text"]).group(1)
    message = f"Here are all the pods in `{namespace}` I can find:\n" + "\n".join(
        [pod.metadata.name for pod in k.list_namespaced_pod(namespace).items]
    )
    send_message(message, payload)


@register(r"(?:get|list) pods?$")
def list_all_pods(**payload):
    """
    List all the Pods in a cluster
    """
    pod_list = [
        pod.metadata.name for pod in k.list_pod_for_all_namespaces(watch=False).items
    ]
    message = "Here are all the pods I can find:\n" + "\n".join(pod_list)
    send_message(message, payload)


@register(r"(?:get|list) logs? for pod (\S+)$")
def pod_logs(**payload):
    """
    Get logs for a given pod
    """
    pod_name = re.search(payload["regex"], payload["data"]["text"]).group(1)
    pod = next(
        (
            pod
            for pod in k.list_pod_for_all_namespaces(watch=False).items
            if pod_name in pod.metadata.name
        ),
        None,
    )
    logging.debug(f"found this pod: {pod}")
    if not pod:
        send_message(
            f"Could not find pod named {pod_name}. Did you type it correctly?", payload
        )
    else:
        message = (f"Here are the logs from `{pod_name}`",)
        file = k.read_namespaced_pod_log(pod_name, pod.metadata.namespace)
        send_file(message, file, payload)


@register(r"(?:get|list) previous logs? for pod (\S+)$")
def previous_pod_logs(**payload):
    """
    Get logs for a previous instance of a given pod
    """
    pod_name = re.search(payload["regex"], payload["data"]["text"]).group(1)
    pod = next(
        (
            pod
            for pod in k.list_pod_for_all_namespaces(watch=False).items
            if pod_name in pod.metadata.name
        ),
        None,
    )
    logging.debug(f"found this pod: {pod}")
    if not pod:
        send_message(
            f"Could not find pod named {pod_name}. Did you type it correctly?", payload
        )
    else:
        message = (f"Here are the logs from `{pod_name}`",)
        file = k.read_namespaced_pod_log(
            pod_name, pod.metadata.namespace, previous=True
        )
        send_file(message, file, payload)


@register(r"(get|list) namespaces$")
def list_namespaces(**payload):
    """
    List all namespaces in a cluster.
    """
    ns_list = [ns.metadata.name for ns in k.list_namespace().items]
    message = "Here are all the namespaces I can find:\n" + "\n".join(ns_list)
    send_message(message, payload)


@register(r"describe pod (.+)")
def describe_pod(**payload):
    """
    Get details about a pod include env vars and other useful info
    """
    pod_name = re.search(payload["regex"], payload["data"]["text"]).group(1)
    pod = next(
        (
            pod
            for pod in k.list_pod_for_all_namespaces(watch=False).items
            if pod_name in pod.metadata.name
        ),
        None,
    )
    logging.debug(f"found this pod: {pod}")
    if not pod:
        send_message(
            f"Could not find pod named {pod_name}. Did you type it correctly?", payload
        )
    else:
        message = (f"Here is the description for pod {pod_name}",)
        file = k.read_namespaced_pod(pod_name, pod.metadata.namespace, pretty="true")
        send_file(message, file, payload)


if __name__ == "__main__":
    run()
