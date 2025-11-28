*** Settings ***
Resource    ${CURDIR}/../resources/infra/browser_keywords.robot
Resource    ${CURDIR}/../resources/domain/multicte_keywords.robot

Suite Setup    Initialize Test Suite

*** Test Cases ***
Upload Multi CTE For Emissor
    [Documentation]    Upload Multi CTE files for a specific emissor.
    Start Browser
    Login To MultiCTE
    Navigate To Leitura De Canhotos
    Search And Select Emissor
    Select Delivery Date And Trigger Upload
    Close Browser

*** Keywords ***
Initialize Test Suite
    [Documentation]    Initialize test suite: disable screenshots.
    Set Screenshot Directory    ${None}

