*** Settings ***
Library           SeleniumLibrary

*** Variables ***
${DOWNLOAD_DIR}    ${CURDIR}/../../../../shared/downloads

*** Keywords ***
Start Browser
    ${download_dir}=    Evaluate    os.path.abspath(os.path.normpath(r"${DOWNLOAD_DIR}"))    os
    Log    Configuring browser download directory: ${download_dir}
    ${options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys, selenium.webdriver
    Call Method    ${options}    add_argument    --disable-notifications
    Call Method    ${options}    add_argument    --disable-features\=PushMessaging
    Call Method    ${options}    add_argument    --disable-logging
    Call Method    ${options}    add_argument    --log-level\=3
    # Add arguments to prevent browser disconnection issues
    Call Method    ${options}    add_argument    --no-sandbox
    Call Method    ${options}    add_argument    --disable-dev-shm-usage
    Call Method    ${options}    add_argument    --disable-gpu
    # Set page load timeout to prevent hanging
    ${prefs}=    Create Dictionary    download.default_directory=${download_dir}    download.prompt_for_download=${False}    download.directory_upgrade=${True}
    Call Method    ${options}    add_experimental_option    prefs    ${prefs}
    ${exclude_switches}=    Evaluate    ['enable-logging']
    Call Method    ${options}    add_experimental_option    excludeSwitches    ${exclude_switches}
    Open Browser    about:blank    chrome    options=${options}
    # Set timeouts to prevent session disconnection
    Set Selenium Timeout    30 seconds
    Set Selenium Implicit Wait    10 seconds
    Maximize Browser Window
    # Explicitly disable screenshot capture to avoid saving screenshot files and connection errors
    ${none_value}=    Evaluate    None
    Set Screenshot Directory    ${none_value}

Close Browser
    # Disable screenshots before closing to prevent connection errors
    TRY
        Set Screenshot Directory    ${None}
    EXCEPT
        # Ignore if screenshot directory setting fails
        No Operation
    END
    TRY
        Close All Browsers
    EXCEPT    AS    ${error}
        Log    Error closing browser: ${error}
        # Try to close any remaining browser instances
        TRY
            Close Browser
        EXCEPT
            Log    Could not close browser, continuing
        END
    END

Nothing
    [Documentation]    Dummy keyword to use as run_on_failure to prevent automatic screenshots
    [Arguments]    ${message}=${EMPTY}
    # Do nothing - this prevents SeleniumLibrary from taking screenshots on failure
    RETURN
