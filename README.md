# Edging Firefox 😉

On Windows various Microsoft sites utilize the program `BrowserCore.exe` to retrieve a PRT Cookie to enable seemless authentication with the signed in Windows Account. In order to communicate with this .exe MS uses the Chrome extension [Windows Accounts](https://chrome.google.com/webstore/detail/windows-accounts/ppnbnpeolgkicgegkbkbjmhlideopiji) which communicates via `NativeHostMessaging` to `BrowserCore.exe`.

MS Edge on linux does the same thing, but does it without any extension, instead using `dbus` communication with the program `/opt/microsoft/identity-broker/lib/LinuxBroker-1.6.0.jar` (via https://ubuntu.pkgs.org/20.04/microsoft-prod-amd64/microsoft-identity-broker_1.2.0_amd64.deb.html). This is all coordinated via `intune-portal` which also checks if your computer is "compliant" with company policy.

By abusing a now deprecated [Firefox version](https://addons.mozilla.org/en-US/firefox/addon/windows-10-accounts-port/) of the "Windows Accounts" extension and a custom Native Messaging Host program we can make a request on the `dbus` for a PRT token in the same way as `BrowserCore.exe` on Windows and thus skip the need to type in our password if we're auth'd via Intune.

## Setup

1. Install the extension `windows_accounts_firefox.xpi`
2. 
3. Create the file `~/.mozilla/com.microsoft.browsercore.json` and fill it with

```json
{
    "allowed_extensions": [
        "linux-windows-login@com.elsevier.varesp"
    ],
    "description": "BrowserCore",
    "name": "com.microsoft.browsercore",
    "path": "/home/varesp/test/intune-testing/dbus_testing/test.py",
    "type": "stdio"
}
```
3. 

https://dirkjanm.io/abusing-azure-ad-sso-with-the-primary-refresh-token/