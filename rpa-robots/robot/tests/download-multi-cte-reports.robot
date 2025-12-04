*** Settings ***
Resource    ${CURDIR}/../resources/infra/browser_keywords.robot
Resource    ${CURDIR}/../resources/domain/multicte_keywords.robot

Suite Setup    Initialize Test Suite

*** Test Cases ***
Download Multi CTE Reports
    [Documentation]    Download Multi CTE reports (Excel and PDF) for Canhotos.
    Start Browser
    Login To MultiCTE
    Navigate To Canhotos Relatorios
    Select Report Date
    Select Report
    Preview
    Select Report Campos
    Generate Excel Report
    Generate PDF Report
    Close Browser

*** Keywords ***
Initialize Test Suite
    [Documentation]    Initialize test suite: disable screenshots.
    Set Screenshot Directory    ${None}


