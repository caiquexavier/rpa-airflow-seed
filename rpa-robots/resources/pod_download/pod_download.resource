*** Settings ***
Library           Browser

*** Variables ***
${BASE_URL}    https://mrc-hml.signa.net.br/
${USUARIO}     RPA001
${SENHA}       GL@balti@2025

*** Keywords ***
Login To e-Cargo
    [Arguments]    ${base_url}=${BASE_URL}
    New Page            ${base_url}
    Wait For Elements State    css=#email         visible    timeout=15s
    Fill Text                  css=#email         ${USUARIO}
    Wait For Elements State    css=#password     visible    timeout=15s
    Fill Text                  css=#password     ${SENHA}
    Wait For Elements State    css=#login        enabled    timeout=15s
    Click                      css=#login
    Sleep                     2s

Open Operacional Menu
    Wait For Elements State    text=Operacional    visible    timeout=10s
    Click    text=Operacional
    Sleep    3s
    Take Screenshot    filename=after_operacional_click.png

Open Registro De Canhotos Submenu
    Wait For Elements State    xpath=//div[@class='v-list__tile__title' and text()='Registro de Canhotos']    visible    timeout=10s
    Click    xpath=//div[@class='v-list__tile__title' and text()='Registro de Canhotos']
    Sleep    5s
    Take Screenshot    filename=after_registro_click.png

Input Nota Fiscal And Search
    Sleep    5s
    Fill Text                  css=input[type="text"]    5043156
    Wait For Elements State    css=button[ng-click="viewModel.pesquisar()"]    enabled    timeout=10s
    Click                      css=button[ng-click="viewModel.pesquisar()"]