*** Settings ***
Library           SeleniumLibrary

*** Variables ***
${BASE_URL}    https://mrc-hml.signa.net.br/
${USUARIO}     RPA001
${SENHA}       GL@balti@2025
${NOTA_FISCAL}    1234

*** Keywords ***
Login To e-Cargo
    [Arguments]    ${base_url}=${BASE_URL}
    Go To    ${base_url}
    Wait Until Element Is Visible    css=#email    timeout=15s
    Input Text    css=#email    ${USUARIO}
    Wait Until Element Is Visible    css=#password    timeout=15s
    Input Text    css=#password    ${SENHA}
    Wait Until Element Is Enabled    css=#login    timeout=15s
    Click Element    css=#login
    Sleep    2s

Open Operacional Menu
    Wait Until Element Is Visible    xpath=//*[contains(text(),'Operacional')]    timeout=10s
    Click Element    xpath=//*[contains(text(),'Operacional')]
    Sleep    3s

Open Registro De Canhotos Submenu
    Wait Until Element Is Visible    xpath=//div[@class='v-list__tile__title' and text()='Registro de Canhotos']    timeout=10s
    Click Element    xpath=//div[@class='v-list__tile__title' and text()='Registro de Canhotos']
    Sleep    5s

Input Nota Fiscal And Search
    Wait Until Element Is Visible    css=iframe#frame    timeout=15s
    Select Frame    css=iframe#frame
    Wait Until Element Is Visible    css=input[name="txtNotaFiscal"]    timeout=15s
    # Click to focus on the text input before entering value
    Click Element    css=input[name="txtNotaFiscal"]
    Input Text    css=input[name="txtNotaFiscal"]    ${NOTA_FISCAL}
    Sleep    10s
    Unselect Frame