*** Settings ***
Library           SeleniumLibrary

*** Variables ***
${DOWNLOAD_DIR}    ${CURDIR}/../../../assets/download

*** Keywords ***
Start Browser
    ${download_dir}=    Evaluate    os.path.abspath(os.path.normpath(r"${DOWNLOAD_DIR}"))    os
    ${options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys, selenium.webdriver
    Call Method    ${options}    add_argument    --disable-notifications
    Call Method    ${options}    add_argument    --disable-features\=PushMessaging
    Call Method    ${options}    add_argument    --disable-logging
    Call Method    ${options}    add_argument    --log-level\=3
    ${prefs}=    Create Dictionary    download.default_directory=${download_dir}
    Call Method    ${options}    add_experimental_option    prefs    ${prefs}
    ${exclude_switches}=    Evaluate    ['enable-logging']
    Call Method    ${options}    add_experimental_option    excludeSwitches    ${exclude_switches}
    Open Browser    about:blank    chrome    options=${options}
    Maximize Browser Window

Close Browser
    Close All Browsers
