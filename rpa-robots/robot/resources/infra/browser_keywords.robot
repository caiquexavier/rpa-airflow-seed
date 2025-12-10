*** Settings ***
Library           SeleniumLibrary
Library           OperatingSystem
Library           Collections

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
    ${prefs}=    Create Dictionary
    ...    download.default_directory=${download_dir}
    ...    download.prompt_for_download=${False}
    ...    download.directory_upgrade=${True}
    ...    profile.default_content_setting_values.automatic_downloads=${1}
    ...    profile.content_settings.exceptions.automatic_downloads.*.setting=${1}
    ...    safebrowsing.enabled=${False}
    ...    safebrowsing.disable_download_protection=${True}
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
    # Configure screenshots to be saved in results folder (OUTPUT_DIR) instead of root folder
    # OUTPUT_DIR is automatically set by Robot Framework to the --outputdir value
    Configure Screenshot Directory

Close Browser
    TRY
        Close All Browsers
    EXCEPT    AS    ${error}
        TRY
            Close Browser
        EXCEPT
            No Operation
        END
    END

Configure Screenshot Directory
    [Documentation]    Configure screenshot directory to save screenshots in results folder (OUTPUT_DIR).
    ...                This ensures screenshots are saved in the results folder, not the root folder.
    ${output_dir}=    Get Variable Value    ${OUTPUT_DIR}    ${EMPTY}
    IF    '${output_dir}' == '${EMPTY}'
        # Fallback: try to use results directory relative to current directory
        ${results_dir}=    Evaluate    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(r"${CURDIR}")))), "results")    os
        ${results_dir_abs}=    Evaluate    os.path.abspath(r"${results_dir}")    os
        Set Screenshot Directory    ${results_dir_abs}
        Log    Screenshot directory set to: ${results_dir_abs}    level=INFO
    ELSE
        Set Screenshot Directory    ${output_dir}
        Log    Screenshot directory set to: ${output_dir}    level=INFO
    END

Cleanup Screenshots
    [Documentation]    Clean up all selenium screenshots from the results folder after test execution.
    ...                This should be called in Suite Teardown or Test Teardown.
    ${output_dir}=    Get Variable Value    ${OUTPUT_DIR}    ${EMPTY}
    IF    '${output_dir}' == '${EMPTY}'
        # Fallback: try to use results directory relative to current directory
        ${results_dir}=    Evaluate    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(r"${CURDIR}")))), "results")    os
        ${results_dir_abs}=    Evaluate    os.path.abspath(r"${results_dir}")    os
        ${cleanup_dir}=    Set Variable    ${results_dir_abs}
    ELSE
        ${cleanup_dir}=    Set Variable    ${output_dir}
    END
    
    ${dir_exists}=    Run Keyword And Return Status    Directory Should Exist    ${cleanup_dir}
    IF    not ${dir_exists}
        Log    Results directory does not exist: ${cleanup_dir}. Skipping screenshot cleanup.    level=WARN
        RETURN
    END
    
    # Clean up selenium screenshots
    ${screenshot_patterns}=    Create List    selenium-screenshot-*.png    selenium-screenshot-*.jpg    selenium-screenshot-*.jpeg
    ${deleted_count}=    Set Variable    ${0}
    
    FOR    ${pattern}    IN    @{screenshot_patterns}
        ${files}=    List Files In Directory    ${cleanup_dir}    pattern=${pattern}
        FOR    ${file}    IN    @{files}
            TRY
                ${file_path}=    Evaluate    os.path.join(r"${cleanup_dir}", r"${file}")    os
                Remove File    ${file_path}
                ${deleted_count}=    Evaluate    ${deleted_count} + 1
                Log    Deleted screenshot: ${file}    level=DEBUG
            EXCEPT    AS    ${error}
                Log    Failed to delete screenshot ${file}: ${error}    level=WARN
            END
        END
    END
    
    IF    ${deleted_count} > 0
        Log    Cleaned up ${deleted_count} screenshot(s) from ${cleanup_dir}    level=INFO
    END

