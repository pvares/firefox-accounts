#!/usr/bin/env python3.10
# pylint: disable=line-too-long
"""A python program which aims to replicate the function of `BrowserCore.exe` on windows using the LinuxBroker dbus interface"""

import argparse
import json
import logging
import os
import struct
import sys

from urllib.parse import unquote

import dbus

bus = dbus.SessionBus()

obj = bus.get_object("com.microsoft.identity.broker1", "/com/microsoft/identity/broker1")
iface = dbus.Interface(obj, dbus_interface="com.microsoft.identity.Broker1")

EXTENSION_ID = "linux-windows-login@com.elsevier.varesp"


def parse_args() -> argparse.Namespace:
    """Parse Arguments

    :return: args
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        "A python library to facilitate Native Host Messaging with MS for seamless cookie auth"
    )
    parser.add_argument(
        "--logfile",
        help="A file to log requests to. If a '-' is provided, will log to `stderr`. If omitted, will not log",
    )
    parser.add_argument(
        "--verbose",
        help="If provided will log a significant amount of potentially sensitive data.",
        action="store_true",
    )
    parser.add_argument(
        "--install",
        help="Install the Native Hosts file into Firefox for the current user and exit",
        action="store_true",
    )
    parser.add_argument(
        "--install-application-path",
        help=f"The path where this executable to be launched by Firefox is located. Default {sys.argv[0]}",
        default=sys.argv[0],
    )

    # NativeMessagingHosts launches with some arguments (messaging.hosts.file.json, extension@extension-id)
    # we dont want to parse those
    args, _ = parser.parse_known_args()
    return args


def install_native_hosts(install_application_path: str):
    """Install the Native Messaging Hosts file in ~/.mozilla/native-messaging-hosts"""
    native_hosts_json = {
        "allowed_extensions": [EXTENSION_ID],
        "description": "BrowserCore",
        "name": "com.microsoft.browsercore",
        "path": install_application_path,
        "type": "stdio",
    }
    native_hosts_filename = "com.microsoft.browsercore.json"
    native_hosts_path = os.path.join(
        os.path.expanduser("~"), ".mozilla", "native-messaging-hosts", native_hosts_filename
    )
    with open(native_hosts_path, "w", encoding="utf8") as fout:
        json.dump(native_hosts_json, fout, indent=2)
    print(f"Installed to '{native_hosts_path}' with application path '{install_application_path}'")


# communication is over stdin/stdout
STDIN_BUFFER = sys.stdin.buffer
STDOUT_BUFFER = sys.stdout.buffer

DEFAULT_LOG_LEVEL = logging.INFO
LOG_FORMAT = "[%(levelname)s] %(asctime)s | %(message)s"


def main():
    """Main function to receive native message and respond with PRT cookie"""
    # pylint: disable=too-many-locals,too-many-statements
    args = parse_args()

    if args.install:
        install_native_hosts(args.install_application_path)
        return

    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = DEFAULT_LOG_LEVEL

    if not args.logfile:
        logging.basicConfig(level=logging.CRITICAL, stream=sys.stderr, format=LOG_FORMAT)
    elif args.logfile == "-":
        logging.basicConfig(level=log_level, stream=sys.stderr, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=log_level, filename=args.logfile, format=LOG_FORMAT)

    # we run in a while loop because it's possible to "receive" a stdin, but it doesn't actually contain any content
    while not STDIN_BUFFER.closed:
        try:
            # read the request from the browser in the native messaging hosts format
            # <u32_length><char*_request>
            # if it's a blank message skip it
            message_size = struct.unpack_from("@i", STDIN_BUFFER.read(4))[0]
            if not message_size:
                continue

            logging.debug("Incoming message of %s bytes", message_size)

            cookie_request = STDIN_BUFFER.read(message_size)
            cookie_request = cookie_request.decode("utf8")
            cookie_request = json.loads(cookie_request)
            logging.debug("Message contents '%s'", json.dumps(cookie_request))

            # parse out the parameters so that they can be provided to the broker
            uri: str = cookie_request["uri"]
            sender: str = cookie_request["sender"]

            if not sender.startswith("https://login.microsoftonline.com/"):
                logging.warning("Unexpected request from '%s'. Aborting", sender)
                return

            params = {}
            uri_params = uri.split("?", 1)[1].split("&")
            for param in uri_params:
                param = unquote(param)
                key, value = param.split("=", 1)
                params[key] = value
            logging.debug("URI params '%s'", json.dumps(params))

            client_id = params["client_id"]
            corr_id = params["client-request-id"]
            redirect_uri = params["redirect_uri"]
            scopes = params["scope"].split(" ")

            # retrieve accounts available on the host
            request_json = json.dumps({"clientId": client_id, "redirectUri": redirect_uri})
            resp = json.loads(iface.getAccounts("0.0", corr_id, request_json))
            # let's just assume it's the only account here... this _could_ be more than 1, but i'm not handling that right now
            account = resp["accounts"][0]

            ##acquirePrtSsoCookie
            request_json = {
                "account": account,
                "authParameters": {
                    "account": account,
                    "authority": "https://login.microsoftonline.com/common",
                    # unsure what this type is, it's not provided in the auth request from the browser
                    "authorizationType": 8,
                    "clientId": client_id,
                    "redirectUri": redirect_uri,
                    "requestedScopes": scopes,
                    "username": account["username"],
                },
                "ssoUrl": uri,
            }
            resp = json.loads(iface.acquirePrtSsoCookie("0.0", corr_id, json.dumps(request_json)))

            # https://dirkjanm.io/abusing-azure-ad-sso-with-the-primary-refresh-token/
            browser_response = {
                "response": [
                    {
                        "name": resp["cookieName"],
                        "data": resp["cookieContent"],
                        # "p3pHeader": "CP=\"CAO DSP COR ADMa DEV CONo TELo CUR PSA PSD TAI IVDo OUR SAMi BUS DEM NAV STA UNI COM INT PHY ONL FIN PUR LOCi CNT\"",
                        # "flags": 8256,
                    }
                ]
            }

            # response must be in binary format
            response = json.dumps(browser_response).encode("utf8")
            # with the length
            response_bytes = struct.pack("@i", len(response))
            logging.debug("Response (%s) '%s'", len(response), json.dumps(browser_response))
            logging.info("Responded to PRT Cookie Request")

            # write the response back out to the browser in the native messaging hosts format
            # <u32_length><char*_response>
            STDOUT_BUFFER.write(response_bytes)
            STDOUT_BUFFER.write(response)
            STDOUT_BUFFER.flush()
            break

        # pylint: disable=broad-exception-caught
        except Exception as exc:
            logging.error("Failed!, %s", exc, exc_info=exc)
            break
