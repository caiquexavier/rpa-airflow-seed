*** Settings ***
Library           Browser

*** Keywords ***
Start Browser
    New Browser         browser=chromium    headless=${False}
    New Context         acceptDownloads=${True}

Close Browser
    Close Context
