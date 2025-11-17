*** Settings ***
Resource    ${CURDIR}/../src/resources/browser/browser.resource
Resource    ${CURDIR}/../src/resources/pod_download/pod_download.resource

Suite Setup    Initialize Test Suite

*** Test Cases ***
Pod Download
    [Documentation]    Execute pod download.
    
    Start Browser
    Login To e-Cargo
    Open Operacional Menu
    Open Registro De Canhotos Submenu
    Process Nota Fiscal Array From Variables
    Close Browser

*** Keywords ***
Initialize Test Suite
    [Documentation]    Initialize test suite: disable screenshots.
    Set Screenshot Directory    ${None}
