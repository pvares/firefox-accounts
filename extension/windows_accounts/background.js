// Copyright (c) 2017 Microsoft Corporation. All rights reserved.

browser.runtime.onMessage.addListener(
    function (request, sender, sendResponse) {
        try {
            // Pass the sender into the native host to validate that the page is able to call this method.
            request.sender = sender.url;

            browser.runtime.sendNativeMessage(
                "com.microsoft.browsercore",
                request,
                function (response) {
                    if (response != null) {
                        if (response.status && response.status == "Fail" && response.code) {
                            sendResponse(response);
                        }
                        else {
                            sendResponse({
                                status: "Success",
                                result: response
                            });
                        }
                    }
                    else {
                        sendResponse({
                            status: "Fail",
                            code: "NoSupport",
                            description: browser.runtime.lastError.message,
                        });
                    }

                });
        }
        catch (e) {
            console.log("Exception!", e)
            sendResponse({
                status: "Fail",
                code: "NoSupport",
                description: e.toString(),
            });
        }

        return true;
    });

browser.browserAction.onClicked.addListener(function (tab) {
    browser.tabs.create({ url: 'https://www.office.com' });
});

// Let Microsoft think we're using Chrome, so the SSO option will be available.
let ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36';
browser.webRequest.onBeforeSendHeaders.addListener(
    function(e) {
        for (let header of e.requestHeaders) {
            if (header.name.toLowerCase() === 'user-agent') {
                header.value = ua;
            }
        }
        return {requestHeaders: e.requestHeaders};
    },
    {urls: ['https://login.microsoftonline.com/*']},
    ["blocking", "requestHeaders"]
);