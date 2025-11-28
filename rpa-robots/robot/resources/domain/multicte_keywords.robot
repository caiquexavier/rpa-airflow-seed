*** Settings ***
Library           SeleniumLibrary
Resource    ${CURDIR}/../infra/ui_keywords.robot
Variables        ${CURDIR}/../../variables/env_vars.py

*** Keywords ***
Login To MultiCTE
    [Documentation]    Login to MultiCTE system using credentials from config.
    [Arguments]    ${base_url}=${MULTICTE_BASE_URL}
    Go To    ${base_url}
    Sleep    3s
    Wait Until Element Is Visible    xpath=//*[@id="Usuario"]    timeout=30s
    Input Text    xpath=//*[@id="Usuario"]    ${MULTICTE_USERNAME}
    Wait Until Element Is Visible    xpath=//*[@id="Senha"]    timeout=30s
    Input Text    xpath=//*[@id="Senha"]    ${MULTICTE_PASSWORD}
    Wait Until Element Is Visible    xpath=//*[@id="login-form"]/div[2]/div[3]/button    timeout=30s
    Click Element    xpath=//*[@id="login-form"]/div[2]/div[3]/button
    Sleep    3s

Navigate To Leitura De Canhotos
    [Documentation]    Navigate to Leitura de Canhotos menu.
    Wait For Element And Click    xpath=//*[@id="js-nav-menu"]/li[6]/a
    Sleep    1s
    Wait For Element And Click    xpath=//*[@id="js-nav-menu"]/li[6]/ul/li[1]/a
    Sleep    1s
    Wait For Element And Click    xpath=//*[@id="js-nav-menu"]/li[6]/ul/li[1]/ul/li[3]/a
    Sleep    2s

Click Emissor Search Button
    [Documentation]    Click the search button to open emissor search modal. Uses multiple fallback strategies to handle dynamic IDs.
    ${search_button_xpath}=    Set Variable    xpath=//button[@aria-label="Buscar" and contains(@class, "btn-primary")]
    ${search_button_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${search_button_xpath}    timeout=10s
    IF    not ${search_button_found}
        ${alt_search_button}=    Set Variable    xpath=//button[@type="button" and @aria-label="Buscar"]
        ${alt_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${alt_search_button}    timeout=10s
        IF    ${alt_found}
            Wait For Element And Click    ${alt_search_button}
        ELSE
            ${icon_search}=    Set Variable    xpath=//button[.//i[contains(@class, "fa-search")]]
            Wait Until Element Is Visible    ${icon_search}    timeout=10s
            Click Element    ${icon_search}
        END
    ELSE
        Wait For Element And Click    ${search_button_xpath}
    END

Input Emissor Razao Social
    [Documentation]    Input emissor code into Razão Social field. Uses multiple fallback strategies to handle dynamic IDs. Waits for input to be fully entered.
    [Arguments]    ${emissor_code}
    ${razao_social_xpath}=    Set Variable    xpath=//input[@type="text" and @aria-label="Razão Social:"]
    ${input_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${razao_social_xpath}    timeout=10s
    IF    not ${input_found}
        ${alt_input_xpath}=    Set Variable    xpath=//input[@type="text" and contains(@class, "form-control") and contains(@aria-label, "Razão Social")]
        ${alt_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${alt_input_xpath}    timeout=10s
        IF    ${alt_found}
            Wait For Element And Click    ${alt_input_xpath}
            Clear Element Text    ${alt_input_xpath}
            Wait For Element And Input Text    ${alt_input_xpath}    ${emissor_code}
            Wait Until Input Value Matches    ${alt_input_xpath}    ${emissor_code}
        ELSE
            Fail    Razão Social input field not found
        END
    ELSE
        Wait For Element And Click    ${razao_social_xpath}
        Clear Element Text    ${razao_social_xpath}
        Wait For Element And Input Text    ${razao_social_xpath}    ${emissor_code}
        Wait Until Input Value Matches    ${razao_social_xpath}    ${emissor_code}
    END

Wait Until Input Value Matches
    [Documentation]    Wait until input field value matches expected value, ensuring input is fully processed.
    [Arguments]    ${input_xpath}    ${expected_value}
    Wait Until Keyword Succeeds    1s    0.5s    Verify Input Value    ${input_xpath}    ${expected_value}

Verify Input Value
    [Documentation]    Verify that input field contains the expected value.
    [Arguments]    ${input_xpath}    ${expected_value}
    ${actual_value}=    Get Value    ${input_xpath}
    Should Be Equal    ${actual_value}    ${expected_value}    Input value does not match expected value

Click Pesquisar Button
    [Documentation]    Click the Pesquisar button to search for emissor. Ensures only the button within the modal receives the click.
    Wait For BlockUI Overlay To Disappear
    ${modal_xpath}=    Set Variable    xpath=//div[contains(@class, "modal") and contains(@class, "show")]
    Wait Until Element Is Visible    ${modal_xpath}    timeout=10s
    ${pesquisar_button_xpath}=    Set Variable    xpath=//div[contains(@class, "modal") and contains(@class, "show")]//button[.//span[text()="Pesquisar"] and contains(@class, "btn-primary")]
    Wait Until Element Is Visible    ${pesquisar_button_xpath}    timeout=10s
    Scroll Element Into View    ${pesquisar_button_xpath}
    Set Focus To Element    ${pesquisar_button_xpath}
    Click Element    ${pesquisar_button_xpath}
    Wait For Search Results

Wait For Search Results
    [Documentation]    Wait for search results table to appear after clicking Pesquisar.
    ${results_table_xpath}=    Set Variable    xpath=//table//tbody//tr
    Wait Until Element Is Visible    ${results_table_xpath}    timeout=15s
    Sleep    0.5s

Click Selecionar Link
    [Documentation]    Click the Selecionar link to select the emissor from search results. Waits for blockUI overlay to disappear before clicking.
    Wait For BlockUI Overlay To Disappear
    ${table_link_xpath}=    Set Variable    xpath=//table//tbody//tr//a[text()="Selecionar"]
    Wait Until Element Is Visible    ${table_link_xpath}    timeout=15s
    Scroll Element Into View    ${table_link_xpath}
    Wait For Element And Click    ${table_link_xpath}

Wait For BlockUI Overlay To Disappear
    [Documentation]    Wait for blockUI overlay to disappear before attempting to click elements.
    ${blockui_overlay_xpath}=    Set Variable    xpath=//div[contains(@class, "blockUI") and contains(@class, "blockOverlay")]
    ${overlay_visible}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${blockui_overlay_xpath}    timeout=2s
    IF    ${overlay_visible}
        Wait Until Element Is Not Visible    ${blockui_overlay_xpath}    timeout=30s
    END

Search And Select Emissor
    [Documentation]    Search for emissor by code and select it. Ensures input is fully entered, Pesquisar is clicked, and results appear before clicking Selecionar.
    [Arguments]    ${emissor_code}=${MULTICTE_EMISSOR_CODE}
    Click Emissor Search Button
    Sleep    0.5s
    Input Emissor Razao Social    ${emissor_code}
    Click Pesquisar Button
    Click Selecionar Link
    Sleep    1s

Select Delivery Date And Trigger Upload
    [Documentation]    Select delivery date and trigger file upload.
    [Arguments]    ${delivery_date}=27/11/2025
    Click Delivery Date Picker
    Input Delivery Date    ${delivery_date}
    Click Upload Button
    Sleep    2s

Click Delivery Date Picker
    [Documentation]    Click the delivery date picker button to open date selection.
    ${date_picker_button_xpath}=    Set Variable    xpath=//div[contains(@id, "tempus-dominus-append")]//span[contains(@class, "btn-primary")]//i[contains(@class, "fa-calendar")]
    Wait Until Element Is Visible    ${date_picker_button_xpath}    timeout=10s
    Scroll Element Into View    ${date_picker_button_xpath}
    Set Focus To Element    ${date_picker_button_xpath}
    Click Element    ${date_picker_button_xpath}
    Sleep    1s

Input Delivery Date
    [Documentation]    Input delivery date into the date picker input field.
    [Arguments]    ${delivery_date}
    ${date_input_xpath}=    Set Variable    xpath=//div[contains(@id, "tempus-dominus-append")]/../input
    Wait Until Element Is Visible    ${date_input_xpath}    timeout=5s
    Wait For Element And Input Text    ${date_input_xpath}    ${delivery_date}
    Sleep    1s
    Press Keys    ${date_input_xpath}    RETURN
    Sleep    1s

Click Upload Button
    [Documentation]    Click the upload button to trigger file upload. Uses stable attributes to find the upload label.
    ${upload_button_xpath}=    Set Variable    xpath=//label[contains(@class, "btn-primary") and .//i[contains(@class, "fa-upload")]]
    Wait Until Element Is Visible    ${upload_button_xpath}    timeout=10s
    Scroll Element Into View    ${upload_button_xpath}
    Set Focus To Element    ${upload_button_xpath}
    Click Element    ${upload_button_xpath}

