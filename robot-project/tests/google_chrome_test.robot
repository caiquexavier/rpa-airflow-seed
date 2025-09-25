*** Settings ***
Documentation     Google Chrome test using Robot Framework Browser (Playwright).
Resource          ../resources/common.resource

*** Test Cases ***
Google Chrome Navigation Test
    [Documentation]    Opens Google Chrome, navigates to Google.com, and verifies page title.
    [Setup]           Open Chrome Browser
    [Teardown]        Close Browser And Cleanup
    
    # Navigate to Google homepage
    Go To             https://www.google.com
    
    # Verify page title contains "Google"
    ${title}=         Get Title
    Should Contain    ${title}    Google


