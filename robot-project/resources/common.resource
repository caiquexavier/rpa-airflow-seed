*** Settings ***
Documentation     Common reusable keywords using only built-in libraries.
Library           BuiltIn
Library           Collections
Library           Browser

*** Keywords ***
Should Be Equal Wrapper
    [Documentation]    Assert two values are equal using BuiltIn keyword.
    [Arguments]        ${actual}    ${expected}
    Should Be Equal    ${actual}    ${expected}

Should Contain Substring Wrapper
    [Documentation]    Assert text contains expected substring.
    [Arguments]        ${text}    ${substring}
    Should Contain     ${text}    ${substring}

Create Example Dictionary And Get
    [Documentation]    Create a simple dictionary and return a value by key.
    [Arguments]        ${key}
    ${dct}=            Create Dictionary    a=1    b=2    c=3
    ${value}=          Get From Dictionary  ${dct}    ${key}
    RETURN              ${value}

Open Chrome Browser
    [Documentation]    Opens Google Chrome browser using Playwright.
    New Browser         browser=chromium    headless=False
    New Context         viewport={'width': 1280, 'height': 720}
    New Page

Close Browser And Cleanup
    [Documentation]    Closes browser and cleans up resources.
    Close Browser

