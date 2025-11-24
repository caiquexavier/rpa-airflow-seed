*** Settings ***
Library           SeleniumLibrary
Library           JSONLibrary
Library           Collections
Library           OperatingSystem
Library           ${CURDIR}/../../libs/saga_client.py
Library           ${CURDIR}/../../libs/path_config.py

*** Variables ***
${BASE_URL}   https://ecargo.mercosulline.com.br/
${USUARIO}     RPA001
${SENHA}       Mercosul@25@25
${JSON_DATA}    ${EMPTY}

${XPATH_OPERACIONAL_MENU}    //*[@id="app"]/div[6]/div[1]/aside/div[1]/div[2]/div[5]/div[1]
${XPATH_REGISTRO_CANHOTOS}    //div[@class='v-list__tile__title' and text()='Registro de Canhotos']
${XPATH_SEARCH_BUTTON}    /html/body/div/div/div[3]/form/div[1]/div[6]/div/div[1]/button
${XPATH_ERROR_MODAL}    //*[@id="modalMensagem"]/div/div/div
${XPATH_ERROR_MSG}    //*[@id="modalMensagem"]/div/div/div/div[1]
${XPATH_ERROR_CLOSE}    //*[@id="modalMensagem"]/div/div/div/div[2]/button
${XPATH_CANHOTO_BUTTON}    /html/body/div/div/div[3]/form/div[2]/div[2]/table/tbody/tr[2]/td/div/div[2]/div[3]/button
${XPATH_MODAL_CANHOTO}    //*[@id="ModalCanhotoNf"]

*** Keywords ***
Load JSON Data
    [Arguments]    ${payload}
    ${parsed}=    Convert Saga Payload To Dict    ${payload}
    ${has_doc_list}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${parsed}    doc_transportes_list
    IF    ${has_doc_list}
        Set Global Variable    ${JSON_DATA}    ${parsed}
    ELSE
        ${data_node}=    Get From Dictionary    ${parsed}    data
        Set Global Variable    ${JSON_DATA}    ${data_node}
    END

Get Saga Doc Transportes List
    ${doc_list}=    Get From Dictionary    ${JSON_DATA}    doc_transportes_list
    Should Not Be Empty    ${doc_list}    doc_transportes_list não encontrado ou vazio no payload do SAGA
    RETURN    ${doc_list}

Login To e-Cargo
    [Arguments]    ${base_url}=${BASE_URL}
    Go To    ${base_url}
    Sleep    3s
    ${email_selector}=    Set Variable    css=#email
    ${email_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${email_selector}    timeout=10s
    IF    not ${email_found}
        ${email_selector}=    Set Variable    css=input[type="email"]
        ${email_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${email_selector}    timeout=5s
        IF    not ${email_found}
            ${email_selector}=    Set Variable    css=input[name="email"]
            ${email_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${email_selector}    timeout=5s
        END
    END
    IF    not ${email_found}
        Fail    Email field not found on login page após 20 segundos.
    END
    Input Text    ${email_selector}    ${USUARIO}
    Wait Until Element Is Visible    css=#password    timeout=30s
    Input Text    css=#password    ${SENHA}
    Wait Until Element Is Enabled    css=#login    timeout=30s
    Click Element    css=#login
    Sleep    2s

Open Operacional Menu
    Wait Until Element Is Visible    xpath=${XPATH_OPERACIONAL_MENU}    timeout=10s
    Click Element    xpath=${XPATH_OPERACIONAL_MENU}
    Sleep    1s

Open Registro De Canhotos Submenu
    TRY
        Wait Until Element Is Visible    xpath=${XPATH_REGISTRO_CANHOTOS}    timeout=10s
        Click Element    xpath=${XPATH_REGISTRO_CANHOTOS}
        Sleep    2s
    EXCEPT    AS    ${error}
        Fail    Failed to open Registro de Canhotos: ${error}
    END

Input Nota Fiscal
    [Arguments]    ${nota_fiscal}
    Wait Until Element Is Visible    css=iframe#frame    timeout=15s
    Select Frame    css=iframe#frame
    Wait Until Element Is Visible    css=input[name="txtNotaFiscal"]    timeout=15s
    Clear Element Text    css=input[name="txtNotaFiscal"]
    Input Text    css=input[name="txtNotaFiscal"]    ${nota_fiscal}

Search Nota Fiscal
    [Arguments]    ${nota_fiscal}
    Wait Until Element Is Visible    xpath=${XPATH_SEARCH_BUTTON}    timeout=10s
    Scroll Element Into View    xpath=${XPATH_SEARCH_BUTTON}
    Wait Until Element Is Enabled    xpath=${XPATH_SEARCH_BUTTON}    timeout=5s
    Wait Until Keyword Succeeds    3x    1s    Click Element    xpath=${XPATH_SEARCH_BUTTON}
    Sleep    1s
    
    ${has_error_modal}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=${XPATH_ERROR_MODAL}    timeout=3s
    IF    ${has_error_modal}
        ${error_msg}=    Get Text    xpath=${XPATH_ERROR_MSG}
        Click Element    xpath=${XPATH_ERROR_CLOSE}
        Sleep    1s
        Unselect Frame
        Fail    Error modal apareceu durante pesquisa da nota ${nota_fiscal}: ${error_msg}
    END
    
    ${search_success}=    Run Keyword And Return Status    Wait Until Keyword Succeeds    5s    0.5s    Verify Search Results Appeared
    IF    not ${search_success}
        Unselect Frame
        Fail    Pesquisa não retornou resultados visíveis para nota fiscal ${nota_fiscal}
    END
    RETURN    ${True}

Verify Search Results Appeared
    ${table_visible}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=//table//tbody/tr    timeout=3s
    RETURN    ${table_visible}

Validate Nota Fiscal Search
    [Arguments]    ${nota_fiscal}
    ${result}=    Search Nota Fiscal    ${nota_fiscal}
    Should Be True    ${result}    Falha ao pesquisar nota fiscal ${nota_fiscal}

Open Nota Fiscal Modal
    [Documentation]    Opens the nota fiscal modal. Returns dict with status and error_message if business error occurs.
    Click Nota Fiscal Expand Button
    Wait Until Element Is Visible    xpath=${XPATH_CANHOTO_BUTTON}    timeout=10s
    Click Element    xpath=${XPATH_CANHOTO_BUTTON}
    Sleep    1s
    ${has_error_modal}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=${XPATH_ERROR_MODAL}    timeout=3s
    IF    ${has_error_modal}
        ${error_msg}=    Get Text    xpath=${XPATH_ERROR_MSG}
        Click Element    xpath=${XPATH_ERROR_CLOSE}
        Sleep    1s
        Cleanup Nota Fiscal Frame
        ${error_result}=    Create Dictionary    status=FAIL    error_message=${error_msg}
        RETURN    ${error_result}
    END
    Wait Until Element Is Visible    xpath=${XPATH_MODAL_CANHOTO}    timeout=10s
    ${success_result}=    Create Dictionary    status=SUCCESS    error_message=${EMPTY}
    RETURN    ${success_result}

Download Nota Fiscal Pdfs
    Download All PDF Files
    Sleep    0.5s

Close Nota Fiscal Modal
    ${sair_button}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=${XPATH_MODAL_CANHOTO}//button[contains(.,'Sair') or contains(.,'sair')]    timeout=3s
    IF    ${sair_button}
        Click Element    xpath=${XPATH_MODAL_CANHOTO}//button[contains(.,'Sair') or contains(.,'sair')]
        Sleep    1s
    ELSE
        ${close_button}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=${XPATH_MODAL_CANHOTO}//button[contains(@class,'close') or contains(@ng-click,'close')]    timeout=2s
        IF    ${close_button}
            Click Element    xpath=${XPATH_MODAL_CANHOTO}//button[contains(@class,'close') or contains(@ng-click,'close')]
            Sleep    1s
        ELSE
            Log    Sair or close button not detected for nota fiscal modal    level=WARN
        END
    END
    Cleanup Nota Fiscal Frame

Cleanup Nota Fiscal Frame
    Run Keyword And Ignore Error    Unselect Frame

Click Nota Fiscal Expand Button
    ${plus_xpath}=    Set Variable    /html/body/div/div/div[3]/form/div[2]/div[2]/table/tbody/tr[1]/td[10]/i
    Wait Until Element Is Visible    xpath=${plus_xpath}    timeout=10s
    Scroll Element Into View    xpath=${plus_xpath}
    Wait Until Element Is Enabled    xpath=${plus_xpath}    timeout=5s
    Wait Until Keyword Succeeds    3x    1s    Click Element    xpath=${plus_xpath}
    Sleep    0.5s

Download All PDF Files
    ${download_dir}=    Evaluate    path_config.get_downloads_dir()    modules=path_config
    ${download_dir_exists}=    Run Keyword And Return Status    Directory Should Exist    ${download_dir}
    IF    not ${download_dir_exists}
        Create Directory    ${download_dir}
    END
    ${pdf_buttons_count}=    Get Element Count    xpath=${XPATH_MODAL_CANHOTO}//button[contains(@ng-click, 'buscarArquivo') and contains(., 'Pdf')]
    FOR    ${index}    IN RANGE    1    ${pdf_buttons_count} + 1
        ${button_xpath}=    Set Variable    (${XPATH_MODAL_CANHOTO}//button[contains(@ng-click, 'buscarArquivo') and contains(., 'Pdf')])[${index}]
        Wait Until Element Is Visible    xpath=${button_xpath}    timeout=5s
        Wait Until Element Is Enabled    xpath=${button_xpath}    timeout=2s
        Click Element    xpath=${button_xpath}
        Sleep    1s
    END

Convert Saga Payload To Dict
    [Arguments]    ${payload}
    ${is_string}=    Evaluate    isinstance(${payload}, str)
    IF    ${is_string}
        ${result}=    Convert String To Json    ${payload}
    ELSE
        ${result}=    Set Variable    ${payload}
    END
    RETURN    ${result}

