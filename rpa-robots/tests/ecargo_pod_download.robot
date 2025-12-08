*** Settings ***
Resource    ${CURDIR}/../resources/browser/browser.resource
Resource    ${CURDIR}/../resources/pod_download/pod_download.resource

*** Test Cases ***
Pod Download
    Start Browser
    Login To e-Cargo
    Open Operacional Menu
    Open Registro De Canhotos Submenu
    Input Nota Fiscal And Search
    Close Browser