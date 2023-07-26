# Edging Firefox 😉

On Windows various Microsoft sites utilize the program `BrowserCore.exe` to retrieve a PRT Cookie to enable seemless authentication with the signed in Windows Account. In order to communicate with this .exe MS uses the Chrome extension [Windows Accounts](https://chrome.google.com/webstore/detail/windows-accounts/ppnbnpeolgkicgegkbkbjmhlideopiji) which communicates via `NativeHostMessaging` to `BrowserCore.exe`.

MS Edge on linux does the same thing, but does it without any extension, instead using `dbus` communication with the program `/opt/microsoft/identity-broker/lib/LinuxBroker-1.6.0.jar` (via [microsoft-identity-broker](https://ubuntu.pkgs.org/20.04/microsoft-prod-amd64/microsoft-identity-broker_1.2.0_amd64.deb.html)). This is all coordinated via `intune-portal` which also checks if your computer is "compliant" with company policy.

By abusing a now deprecated [Firefox version](https://addons.mozilla.org/en-US/firefox/addon/windows-10-accounts-port/) of the "Windows Accounts" extension and a custom Native Messaging Host program we can make a request on the `dbus` for a PRT token in the same way as `BrowserCore.exe` on Windows and thus skip the need to type in our password if we're auth'd via Intune.

## Setup

1. Install the extension `windows_accounts_firefox.xpi`
2. Install the python wheel "user wide" `pip install linux_browsercore-0.0.1-py3-none-any.whl`
3. Run `browsercore --install` to setup the Native Messaging Hosts file. Check `~/.mozilla/native-messaging-hosts/` for it

## Debugging

If it's not working, don't be shocked. This is held together with paperclips and bits of twine. You can modify `~/.mozilla/native-messaging-hosts/com.microsoft.browsercore.json` to set the path to `browsercore-debug` and check `~/browsercore.log` to potentially get some insight. You can also check the browser console to see if there are messages similar to this:

```BSSO Telemetry: {"result":"Reload","error":null,"type":"ChromeSsoTelemetry","data":{"extension.id":"linux-windows-login@com.elsevier.varesp"},"traces":["BrowserSSO Initialized","Creating ChromeBrowserCore provider","Sending message for method CreateProviderAsync","Received message for method CreateProviderAsync","Using Chrome extension with id linux-windows-login@com.elsevier.varesp","Pulling SSO cookies","Sending message for method GetCookies","Received message for method Response","SSO cookie detected. Refreshing page."]}```

This can help determine if there are any errors

## How it works

### Frontend

On windows there is an executable called `BrowserCore.exe` which handles this interaction via exactly the same mechanisms. This simply replicates that and adds a Firefox extension to facilitate it. The extension spoofs the Chrome on Windows useragent for `login.microsoftonline.com` in order for Microsoft to even offer the Cookie login mechanism.

### Backend

On a host with the `microsoft-identity-broker` package installed, there is a program running and communicating on the DBus which allows users to retrieve several "microsoft-y" cookies & tokens. In particular, the method `acquirePrtSsoCookie` which exactly matches the cookie referred to in [this blog](https://dirkjanm.io/abusing-azure-ad-sso-with-the-primary-refresh-token/) about BrowserCore.exe. By calling this method with the fields within the request we can simply return the result in the format specified from the blog.


## Further work

There are several other functions in the LinuxBroker dbus library which may be worth exploring.

- `acquireTokenInteractively` - ???
- `acquireTokenSilently` - Retrieve a token for accessing things via the MS API
- `getAccounts` - Retrieve a list of accounts available
- `removeAccount` - ???
- `acquirePrtSsoCookie` - Retrieve a PRT cookie for browser auth
- `generateSignedHttpRequest` - ???
- `cancelInteractiveFlow` - ???
- `getLinuxBrokerVersion` - ???
