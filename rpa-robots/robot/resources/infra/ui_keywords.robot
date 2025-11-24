*** Settings ***
Library           SeleniumLibrary

*** Keywords ***
Wait For Element And Click
    [Arguments]    ${locator}    ${timeout}=10s
    [Documentation]    Wait for element to be visible and click it.
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    Click Element    ${locator}

Wait For Element And Input Text
    [Arguments]    ${locator}    ${text}    ${timeout}=10s
    [Documentation]    Wait for element to be visible and input text.
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    Input Text    ${locator}    ${text}

Wait For Element And Get Text
    [Arguments]    ${locator}    ${timeout}=10s
    [Documentation]    Wait for element to be visible and get its text.
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    ${text}=    Get Text    ${locator}
    RETURN    ${text}

Scroll Element Into View
    [Arguments]    ${locator}
    [Documentation]    Scroll element into view.
    SeleniumLibrary.Scroll Element Into View    ${locator}

