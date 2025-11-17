*** Settings ***
Library           SeleniumLibrary

*** Variables ***
${DOWNLOAD_DIR}    ${CURDIR}/../../../../shared/downloads

*** Keywords ***
Start Browser
    ${download_dir}=    Evaluate    os.path.abspath(os.path.normpath(r"${DOWNLOAD_DIR}"))    os
    ${options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys, selenium.webdriver
    Call Method    ${options}    add_argument    --disable-notifications
    Call Method    ${options}    add_argument    --disable-features\=PushMessaging
    Call Method    ${options}    add_argument    --disable-logging
    Call Method    ${options}    add_argument    --log-level\=3
    Call Method    ${options}    add_argument    --no-sandbox
    Call Method    ${options}    add_argument    --disable-dev-shm-usage
    Call Method    ${options}    add_argument    --disable-gpu
    Call Method    ${options}    add_argument    --disable-software-rasterizer
    Call Method    ${options}    add_argument    --disable-extensions
    Call Method    ${options}    add_argument    --disable-background-networking
    Call Method    ${options}    add_argument    --disable-background-timer-throttling
    Call Method    ${options}    add_argument    --disable-renderer-backgrounding
    Call Method    ${options}    add_argument    --disable-backgrounding-occluded-windows
    Call Method    ${options}    add_argument    --disable-breakpad
    Call Method    ${options}    add_argument    --disable-component-extensions-with-background-pages
    Call Method    ${options}    add_argument    --disable-default-apps
    Call Method    ${options}    add_argument    --disable-hang-monitor
    Call Method    ${options}    add_argument    --disable-prompt-on-repost
    Call Method    ${options}    add_argument    --disable-sync
    Call Method    ${options}    add_argument    --disable-translate
    Call Method    ${options}    add_argument    --metrics-recording-only
    Call Method    ${options}    add_argument    --no-first-run
    Call Method    ${options}    add_argument    --safebrowsing-disable-auto-update
    Call Method    ${options}    add_argument    --enable-automation
    Call Method    ${options}    add_argument    --password-store\=basic
    Call Method    ${options}    add_argument    --use-mock-keychain
    ${prefs}=    Create Dictionary    download.default_directory=${download_dir}    download.prompt_for_download=${False}    download.directory_upgrade=${True}
    Call Method    ${options}    add_experimental_option    prefs    ${prefs}
    ${exclude_switches}=    Evaluate    ['enable-logging', 'enable-automation']
    Call Method    ${options}    add_experimental_option    excludeSwitches    ${exclude_switches}
    ${use_automation_extension}=    Evaluate    False
    Call Method    ${options}    add_experimental_option    useAutomationExtension    ${use_automation_extension}
    TRY
        Open Browser    about:blank    chrome    options=${options}
    EXCEPT    AS    ${error}
        ${headless_options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys, selenium.webdriver
        Call Method    ${headless_options}    add_argument    --headless\=new
        Call Method    ${headless_options}    add_argument    --no-sandbox
        Call Method    ${headless_options}    add_argument    --disable-dev-shm-usage
        Call Method    ${headless_options}    add_argument    --disable-gpu
        Call Method    ${headless_options}    add_experimental_option    prefs    ${prefs}
        Call Method    ${headless_options}    add_experimental_option    excludeSwitches    ${exclude_switches}
        Call Method    ${headless_options}    add_experimental_option    useAutomationExtension    ${use_automation_extension}
        Open Browser    about:blank    chrome    options=${headless_options}
    END
    Set Selenium Timeout    30 seconds
    Set Selenium Implicit Wait    10 seconds
    TRY
        Maximize Browser Window
    EXCEPT    AS    ${error}
        No Operation
    END
    ${none_value}=    Evaluate    None
    Set Screenshot Directory    ${none_value}

Close Browser
    TRY
        Set Screenshot Directory    ${None}
    EXCEPT
        No Operation
    END
    TRY
        Close All Browsers
    EXCEPT    AS    ${error}
        TRY
            Close Browser
        EXCEPT
            No Operation
        END
    END
