*** Settings ***
Library           SeleniumLibrary

*** Keywords ***
Start Browser
    Open Browser    about:blank    chrome
    Maximize Browser Window

Close Browser
    Close All Browsers
