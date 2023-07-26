#!/usr/bin/env python3.10
import datetime
import io
import json
import sys
import struct
import traceback
import uuid

from urllib.parse import unquote

import dbus

bus = dbus.SessionBus()

obj = bus.get_object("com.microsoft.identity.broker1", "/com/microsoft/identity/broker1")
iface = dbus.Interface(obj, dbus_interface='com.microsoft.identity.Broker1')

stdin_buffer: io.BufferedReader = sys.stdin.detach()
stdout_buffer: io.BufferedWriter = sys.stdout.detach()

while not stdin_buffer.closed:
    try:
        logfile = open("/home/varesp/test/intune-testing/dbus_testing/logs.log", "a")
        logfile.write(datetime.datetime.now().isoformat() + "\t")

        # read size from buffer
        try:
            # if 4 bytes aren't available, continue till they are
            stdin_buffer.peek(4)
        except:
            continue

        # if it's a blank message skip it
        message_size = struct.unpack_from("@i", stdin_buffer.read(4))[0]
        logfile.write(f"{message_size} - ")
        if not message_size:
            continue

        cookie_request = stdin_buffer.read(message_size)
        cookie_request = cookie_request.decode("utf8")
        logfile.write(f"stdin_closed={stdin_buffer.closed}\t")
        logfile.write(f"{cookie_request}\t")

        cookie_request = json.loads(cookie_request)
        uri:str = cookie_request["uri"]
        logfile.write(uri + "\n")
        logfile.flush()

        # https://login.microsoftonline.com/common/oauth2/authorize?client_id=00000002-0000-0ff1-ce00-000000000000&redirect_uri=https%3a%2f%2foutlook.office.com%2fowa%2f&resource=00000002-0000-0ff1-ce00-000000000000&response_mode=form_post&response_type=code+id_token&scope=openid&msafed=1&msaredir=1&client-request-id=3e0588e7-d5ca-a4ee-1179-885aadf661c3&protectedtoken=true&claims=%7b%22id_token%22%3a%7b%22xms_cc%22%3a%7b%22values%22%3a%5b%22CP1%22%5d%7d%7d%7d&nonce=638259215261827197.22acdb42-381a-4237-b4fd-3ec25e15ef58&state=Dcs7FoAgDAVR0ONyEPMgJCyHb2vp9k1xpxvvnDvNYfxjcVKSgiuIUUghVOUG2pg9IySlFjKShJ73DGkN8CJem9Xbe8X3a_EH&sso_nonce=AwABAAEAAAACAOz_BQD0_568Yt2egb2BV8usOVl4iDr_jSWEKQ8OOwIPcIkyrjqvmsB6cU51fQXHL31drcui-skKr9BySznx8xCirSZlC5cgAA

        uri_params = uri.split("?", 1)[1].split("&")

        params = {}

        for param in uri_params:
            param = unquote(param)
            key, value = param.split("=", 1)
            logfile.write(f"\n\t{key} = {value}")
            params[key] = value
        logfile.write("\n")

        client_id = params["client_id"]
        corr_id = params["client-request-id"]
        redirect_uri = params["redirect_uri"]
        scopes = params["scope"].split(" ")

        requestJson = json.dumps({
            "clientId": client_id,
            "redirectUri": redirect_uri
        })

        resp = json.loads(iface.getAccounts("0.0", corr_id, requestJson))
        for account in resp["accounts"]:
            # print(json.dumps(account, indent=2))
            pass

        ## acquireTokenSilently
        # requestJson = {
        #     "account": account,
        #     "authParameters": {
        #         "account": account,
        #         "authority": "https://login.microsoftonline.com/common",
        #         "authorizationType": 8,
        #         "clientId": outlook_client_id,
        #         "redirectUri": "https://login.microsoftonline.com/common/oauth2/nativeclient",
        #         "requestedScopes": [
        #             "https://graph.microsoft.com/.default",
        #             # "Mail.ReadBasic",
        #         ],
        #         "username": account["username"],
        #     },
        # }
        # resp = json.loads(iface.acquireTokenSilently("0.0", corr_id, json.dumps(requestJson)))


        ##acquirePrtSsoCookie
        requestJson = {
            "account": account,
            "authParameters": {
                "account": account,
                "authority": "https://login.microsoftonline.com/common",
                "authorizationType": 8,
                "clientId": client_id,
                "redirectUri": redirect_uri,
                "requestedScopes": scopes,
                "username": account["username"],
            },
            "ssoUrl": uri
        }
        resp = json.loads(iface.acquirePrtSsoCookie("0.0", corr_id, json.dumps(requestJson)))

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
        
        response = json.dumps(browser_response).encode('utf8')

        response_bytes = struct.pack(f"@i", len(response))

        logfile.write(json.dumps(browser_response) + "\n")
        logfile.flush()

        stdout_buffer.write(response_bytes)
        stdout_buffer.write(response)
        stdout_buffer.flush()
        break

        # print(json.dumps(resp, indent=2))

        # token = resp["brokerTokenResponse"]["accessToken"]
        # params = {"$select": "displayName,jobTitle,userPrincipalName,officeLocation,mail"}
        # params = {}
        # graph_data = requests.get(
        #     f"https://graph.microsoft.com/v1.0/users/nevillek@science.regn.net",
        #     headers={
        #         "Authorization": f"Bearer {token}",
        #     },
        #     params=params,
        #     timeout=30).json()
        # print(json.dumps(graph_data,indent=2))
    except Exception as e:
        logfile.write("Failed!\n")
        traceback.print_exception(e, file=logfile)
        break
        # raise e
    finally:
        logfile.close()