*** Settings ***
Documentation     Minimal deterministic example suite.
Resource          ../../resources/common.resource
Variables         ../../variables/common_variables.py

*** Variables ***
${LOCAL_SUBSTRING}    Robot

*** Test Cases ***
Values Should Be Equal
    [Documentation]    Verify equality using reusable keyword.
    Should Be Equal Wrapper    ${1}    ${1}

Text Should Contain Substring
    [Documentation]    Verify substring presence using resource keyword and variables.
    Should Contain Substring Wrapper    ${EXAMPLE_TEXT}    ${LOCAL_SUBSTRING}

