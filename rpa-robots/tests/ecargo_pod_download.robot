*** Settings ***
Resource    ${CURDIR}/../src/resources/browser/browser.resource
Resource    ${CURDIR}/../src/resources/pod_download/pod_download.resource

*** Test Cases ***
Pod Download
    Start Browser
    Login To e-Cargo
    Open Operacional Menu
    Open Registro De Canhotos Submenu
    Process Nota Fiscal Array From Variables
    Close Browser