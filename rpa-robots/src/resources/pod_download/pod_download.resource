*** Settings ***
Library           SeleniumLibrary
Library           JSONLibrary
Library           Collections
Library           OperatingSystem

*** Variables ***
${BASE_URL}    https://mrc-hml.signa.net.br/
${USUARIO}     RPA001
${SENHA}       Terrific564#TOKIO
${NOTA_FISCAL}    5043156
${JSON_DATA}    ${EMPTY}
${rpa_request}    {"notas_fiscais": []}
@{ERROR_RESULTS}    @{EMPTY}
${RESULT_MESSAGE}    ${EMPTY}

# XPath Selectors
${XPATH_OPERACIONAL_MENU}    //*[contains(text(),'Operacional')]
${XPATH_REGISTRO_CANHOTOS}    //div[@class='v-list__tile__title' and text()='Registro de Canhotos']
${XPATH_SEARCH_BUTTON}    /html/body/div/div/div[3]/form/div[1]/div[6]/div/div[1]/button
${XPATH_ERROR_MODAL}    //*[@id="modalMensagem"]/div/div/div
${XPATH_ERROR_MSG}    //*[@id="modalMensagem"]/div/div/div/div[1]
${XPATH_ERROR_CLOSE}    //*[@id="modalMensagem"]/div/div/div/div[2]/button
${XPATH_CANHOTO_BUTTON}    /html/body/div/div/div[3]/form/div[2]/div[2]/table/tbody/tr[2]/td/div/div[2]/div[3]/button
${XPATH_MODAL_CANHOTO}    //*[@id="ModalCanhotoNf"]

*** Keywords ***
Load JSON Data
    [Arguments]    ${json_string}
    ${is_empty}=    Run Keyword And Return Status    Should Be Equal    ${json_string}    ${EMPTY}
    IF    ${is_empty}
        Set Global Variable    ${JSON_DATA}    {"rpa_request": {"dt_list": []}}
        RETURN
    END
    
    ${is_dict}=    Run Keyword And Return Status    Should Be Equal    ${json_string.__class__.__name__}    dict
    IF    ${is_dict}
        Set Global Variable    ${JSON_DATA}    ${json_string}
    ELSE
        TRY
            ${json_data}=    Convert String To Json    ${json_string}
            Set Global Variable    ${JSON_DATA}    ${json_data}
        EXCEPT    AS    ${error}
            Log    Error parsing JSON: ${error}
            Set Global Variable    ${JSON_DATA}    {"rpa_request": {"dt_list": []}}
        END
    END

Process Nota Fiscal Array
    Initialize Error Results
    TRY
        ${dt_list}=    Get Value From Json    ${JSON_DATA}    $.rpa_request.dt_list[*]
        ${array_length}=    Get Length    ${dt_list}
    EXCEPT    AS    ${error}
        ${error_msg}=    Set Variable    Failed to parse dt_list: ${error}
        Log    ${error_msg}    level=ERROR
        Append Error Result    System    ${error_msg}
        Build Response Message
        RETURN
    END
    
    IF    ${array_length} > 0
        ${success_count}=    Set Variable    0
        ${error_count}=    Set Variable    0
        FOR    ${index}    IN RANGE    0    ${array_length}
            TRY
                ${dt_entry}=    Get Value From Json    ${JSON_DATA}    $.rpa_request.dt_list[${index}]
                ${dt_entry_dict}=    Set Variable    ${dt_entry[0]}
                ${dt_id}=    Get Value From Json    ${dt_entry_dict}    $.dt_id
                ${dt_id_value}=    Set Variable    ${dt_id[0]}
                ${notas_fiscais}=    Get Value From Json    ${dt_entry_dict}    $.notas_fiscais
                ${notas_fiscais_array}=    Set Variable    ${notas_fiscais[0]}
                ${notas_fiscais_length}=    Get Length    ${notas_fiscais_array}
                IF    ${notas_fiscais_length} > 0
                    TRY
                        Open Registro De Canhotos Submenu
                    EXCEPT    AS    ${error}
                        ${error_msg}=    Set Variable    Failed to open submenu: ${error}
                        Log    ${error_msg}    level=ERROR
                        Append Error Result    DT ${dt_id_value}    ${error_msg}
                        CONTINUE
                    END
                    FOR    ${nf_index}    IN RANGE    0    ${notas_fiscais_length}
                        ${current_nota_fiscal}=    Set Variable    ${notas_fiscais_array[${nf_index}]}
                        TRY
                            Process Single Nota Fiscal    ${current_nota_fiscal}
                            ${success_count}=    Evaluate    ${success_count} + 1
                        EXCEPT    AS    ${nf_error}
                            ${error_count}=    Evaluate    ${error_count} + 1
                            ${error_msg}=    Set Variable    ${nf_error}
                            Append Error Result    ${current_nota_fiscal}    ${error_msg}
                        END
                    END
                END
            EXCEPT    AS    ${error}
                ${error_count}=    Evaluate    ${error_count} + 1
                ${error_msg}=    Set Variable    ${error}
                Append Error Result    DT entry ${index + 1}    ${error_msg}
            END
        END
        Log    Processed: ${array_length} | Success: ${success_count} | Errors: ${error_count}    level=INFO
    END
    Build Response Message

Process Nota Fiscal Array From Variables
    ${has_rpa_request}=    Run Keyword And Return Status    Variable Should Exist    ${rpa_request}
    IF    not ${has_rpa_request}
        Fail    rpa_request variable not found
    END
    
    ${notas_fiscais}=    Get Value From Json    ${rpa_request}    $.notas_fiscais
    ${outer_len}=    Get Length    ${notas_fiscais}
    ${actual_array}=    Set Variable    ${EMPTY}
    IF    ${outer_len} > 0
        ${actual_array}=    Set Variable    ${notas_fiscais[0]}
    ELSE
        ${actual_array}=    Create List
    END
    
    ${array_length}=    Get Length    ${actual_array}
    # If no notas fiscais in rpa_request, use default NOTA_FISCAL for manual testing
    IF    ${array_length} == 0
        Log    No notas fiscais found in rpa_request, using default NOTA_FISCAL: ${NOTA_FISCAL}    level=INFO
        Process Single Nota Fiscal    ${NOTA_FISCAL}
    ELSE
        # Process each nota fiscal - fail immediately if any fails
        FOR    ${index}    IN RANGE    0    ${array_length}
            ${current_nota_fiscal}=    Set Variable    ${actual_array[${index}]}
            Process Single Nota Fiscal    ${current_nota_fiscal}
        END
    END

Process Single Nota Fiscal
    [Arguments]    ${nota_fiscal}
    Input Nota Fiscal And Search    ${nota_fiscal}

Login To e-Cargo
    [Arguments]    ${base_url}=${BASE_URL}
    Go To    ${base_url}
    # Wait for page to load completely
    Sleep    3s
    # Wait for email field with timeout
    # Try multiple selectors in case the page structure changed
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
        Fail    Email field not found on login page after 20 seconds. Please check if the page loaded correctly.
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
        ${error_msg}=    Set Variable    Failed to open Registro de Canhotos: ${error}
        Log    ${error_msg}    level=ERROR
        Fail    ${error_msg}
    END

Input Nota Fiscal
    [Arguments]    ${nota_fiscal}=${NOTA_FISCAL}
    # Wait for and select the iframe
    Wait Until Element Is Visible    css=iframe#frame    timeout=15s
    Select Frame    css=iframe#frame
    
    # Wait for and input the nota fiscal
    Wait Until Element Is Visible    css=input[name="txtNotaFiscal"]    timeout=15s
    Clear Element Text    css=input[name="txtNotaFiscal"]
    Input Text    css=input[name="txtNotaFiscal"]    ${nota_fiscal}

Search Nota Fiscal
    [Arguments]    ${nota_fiscal}=${NOTA_FISCAL}
    TRY
        Wait Until Element Is Visible    xpath=${XPATH_SEARCH_BUTTON}    timeout=10s
        Click Element    xpath=${XPATH_SEARCH_BUTTON}
        Sleep    1s
    EXCEPT    AS    ${error}
        ${error_msg}=    Set Variable    Search button not found: ${error}
        Log    ${error_msg}    level=ERROR
        Append Error Result    ${nota_fiscal}    ${error_msg}
        Unselect Frame
        RETURN    ${False}
    END
    
    ${has_error_modal}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=${XPATH_ERROR_MODAL}    timeout=3s
    ${search_success}=    Set Variable    ${True}
    IF    ${has_error_modal}
        TRY
            ${error_msg}=    Get Text    xpath=${XPATH_ERROR_MSG}
            Append Error Result    ${nota_fiscal}    ${error_msg}
            Click Element    xpath=${XPATH_ERROR_CLOSE}
            Sleep    1s
        EXCEPT    AS    ${error}
            ${error_msg}=    Set Variable    Error modal detected but could not read message: ${error}
            Append Error Result    ${nota_fiscal}    ${error_msg}
        END
        Unselect Frame
        ${search_success}=    Set Variable    ${False}
    END
    RETURN    ${search_success}

Handle Error Modal
    [Arguments]    ${nota_fiscal}
    ${error_msg}=    Get Text    xpath=${XPATH_ERROR_MSG}
    Append Error Result    ${nota_fiscal}    ${error_msg}
    Click Element    xpath=${XPATH_ERROR_CLOSE}
    Sleep    1s
    Unselect Frame

Input Nota Fiscal And Search
    [Arguments]    ${nota_fiscal}=${NOTA_FISCAL}
    # Step 1: Navigate to registro canhotos (already done in test)
    # Step 2: Input NF
    Input Nota Fiscal    ${nota_fiscal}
    
    # Step 3: Search for the NF
    ${search_success}=    Search Nota Fiscal    ${nota_fiscal}
    IF    not ${search_success}
        Fail    Failed to search for nota fiscal ${nota_fiscal}
    END
    
    # Step 4: Navigate to Download (click canhoto button)
    Click First Plus Icon With Fallback
    Wait Until Element Is Visible    xpath=${XPATH_CANHOTO_BUTTON}    timeout=10s
    Click Element    xpath=${XPATH_CANHOTO_BUTTON}
    Sleep    1s
    
    # Check for error modal after clicking download button
    ${has_error_modal}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=${XPATH_ERROR_MODAL}    timeout=3s
    IF    ${has_error_modal}
        ${error_msg}=    Get Text    xpath=${XPATH_ERROR_MSG}
        Click Element    xpath=${XPATH_ERROR_CLOSE}
        Sleep    1s
        Unselect Frame
        Fail    Error modal appeared: ${error_msg}
    END
    
    # Step 5: Download PDFs
    Wait Until Element Is Visible    xpath=${XPATH_MODAL_CANHOTO}    timeout=10s
    Download All PDF Files
    Sleep    0.5s
    
    # Close modal if possible
    ${close_button}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=${XPATH_MODAL_CANHOTO}//button[contains(@class,'close') or contains(@ng-click,'close')]    timeout=2s
    IF    ${close_button}
        Click Element    xpath=${XPATH_MODAL_CANHOTO}//button[contains(@class,'close') or contains(@ng-click,'close')]
        Sleep    0.5s
    END
    
    # Unselect frame
    Unselect Frame

Initialize Error Results
    ${list}=    Create List
    Set Global Variable    ${ERROR_RESULTS}    ${list}

Append Error Result
    [Arguments]    ${nota_fiscal}    ${message}
    ${simplified_msg}=    Set Variable    ${message}
    ${msg_length}=    Evaluate    len('${message}')
    IF    ${msg_length} > 200
        ${simplified_msg}=    Evaluate    '${message}'[:200] + '...'
    END
    ${entry}=    Create Dictionary    nota_fiscal=${nota_fiscal}    message=${simplified_msg}
    Append To List    ${ERROR_RESULTS}    ${entry}
    Log    Error for ${nota_fiscal}: ${simplified_msg}    level=ERROR

Build Response Message
    ${has_error_results}=    Run Keyword And Return Status    Variable Should Exist    ${ERROR_RESULTS}
    IF    not ${has_error_results}
        Initialize Error Results
    END
    
    ${error_count}=    Get Length    ${ERROR_RESULTS}
    ${log_message}=    Set Variable    Execution completed successfully.
    ${status}=    Set Variable    PASS
    
    IF    ${error_count} > 0
        ${log_message}=    Set Variable    Execution completed with ${error_count} error(s)
        ${status}=    Set Variable    FAIL
        Log    ${log_message}    level=ERROR
        FOR    ${error}    IN    @{ERROR_RESULTS}
            Log    Critical Error - NF: ${error}[nota_fiscal] | Message: ${error}[message]    level=ERROR
        END
    ELSE
        Log    ${log_message}    level=INFO
    END
    
    ${response}=    Create Dictionary    log=${log_message}    errors=${ERROR_RESULTS}    error_count=${error_count}    status=${status}
    Set Global Variable    ${RESULT_MESSAGE}    ${response}
    
    ${is_fail}=    Evaluate    '${status}' == 'FAIL'
    IF    ${is_fail}
        Fail    ${log_message}
    END

Download All PDF Files
    ${pdf_buttons_count}=    Get Element Count    xpath=${XPATH_MODAL_CANHOTO}//button[contains(@ng-click, 'buscarArquivo') and contains(., 'Pdf')]
    
    # Use the same download directory path as configured in browser.resource
    # From resources/pod_download: go up 4 levels to workspace root, then to shared/downloads
    # Same calculation as browser.resource: ${CURDIR}/../../../../shared/downloads
    ${download_dir}=    Evaluate    os.path.abspath(os.path.normpath(os.path.join(r"${CURDIR}", "..", "..", "..", "..", "shared", "downloads")))    os
    
    ${download_dir_exists}=    Run Keyword And Return Status    Directory Should Exist    ${download_dir}
    IF    not ${download_dir_exists}
        Create Directory    ${download_dir}
    END
    
    Log    Using download directory: ${download_dir}    level=INFO
    
    FOR    ${index}    IN RANGE    1    ${pdf_buttons_count} + 1
        ${button_xpath}=    Set Variable    (${XPATH_MODAL_CANHOTO}//button[contains(@ng-click, 'buscarArquivo') and contains(., 'Pdf')])[${index}]
        Wait Until Element Is Visible    xpath=${button_xpath}    timeout=5s
        ${is_enabled}=    Run Keyword And Return Status    Element Should Be Enabled    xpath=${button_xpath}
        IF    ${is_enabled}
            # Browser downloads to download folder, so check there first
            ${existing_files}=    Evaluate    set([f for f in os.listdir(r"${download_dir}") if f.endswith('.pdf')])    os
            Click Element    xpath=${button_xpath}
            # Wait for download in download folder (where browser saves)
            ${downloaded_file}=    Wait For Download To Complete    ${download_dir}    ${existing_files}    timeout=30s
            # File is already in the correct location, no need to move
            Log    File downloaded to: ${downloaded_file}    level=INFO
        END
    END

Wait For Download To Complete
    [Arguments]    ${download_dir}    ${existing_files_set}    ${timeout}=30s
    ${timeout_seconds}=    Evaluate    int('${timeout}'.replace('s', '')) if 's' in '${timeout}' else int('${timeout}')
    ${max_iterations}=    Evaluate    ${timeout_seconds} * 2
    ${new_file_found}=    Set Variable    ${False}
    ${downloaded_file}=    Set Variable    ${EMPTY}
    
    FOR    ${i}    IN RANGE    ${max_iterations}
        ${all_files_set}=    Evaluate    set([f for f in os.listdir(r"${download_dir}") if f.endswith('.pdf')])    os
        ${new_files}=    Evaluate    list(${all_files_set} - ${existing_files_set})    os
        IF    len(${new_files}) > 0
            ${latest_file}=    Evaluate    max([os.path.join(r"${download_dir}", f) for f in ${new_files}], key=lambda p: os.path.getmtime(p))    os
            ${current_size}=    Evaluate    os.path.getsize(r"${latest_file}")    os
            Sleep    0.5s
            ${new_size}=    Evaluate    os.path.getsize(r"${latest_file}")    os
            IF    ${current_size} == ${new_size} and ${current_size} > 0
                ${new_file_found}=    Set Variable    ${True}
                ${downloaded_file}=    Set Variable    ${latest_file}
                BREAK
            END
        END
        Sleep    0.5s
    END
    
    IF    not ${new_file_found}
        Fail    Download timeout: No new PDF file appeared in ${download_dir} within ${timeout}
    END
    
    RETURN    ${downloaded_file}

Move File To Folder
    [Arguments]    ${source_file}    ${target_dir}
    ${filename}=    Evaluate    os.path.basename(r"${source_file}")    os
    ${target_file}=    Evaluate    os.path.join(r"${target_dir}", r"${filename}")    os
    
    # Ensure target directory exists
    ${target_dir_exists}=    Run Keyword And Return Status    Directory Should Exist    ${target_dir}
    IF    not ${target_dir_exists}
        Create Directory    ${target_dir}
        Log    Created target directory: ${target_dir}    level=INFO
    END
    
    # Verify source file exists
    ${source_exists}=    Run Keyword And Return Status    File Should Exist    ${source_file}
    IF    not ${source_exists}
        Fail    Source file does not exist: ${source_file}
    END
    
    # Move file to target directory
    ${moved}=    Run Keyword And Return Status    Move File    ${source_file}    ${target_file}
    IF    ${moved}
        Log    Successfully moved ${filename} to ${target_dir}    level=INFO
        ${verify_moved}=    Run Keyword And Return Status    File Should Exist    ${target_file}
        IF    not ${verify_moved}
            Fail    File move reported success but target file not found: ${target_file}
        END
    ELSE
        Log    Failed to move ${filename} to ${target_dir}, trying copy    level=WARN
        Copy File    ${source_file}    ${target_file}
        ${copied_exists}=    Run Keyword And Return Status    File Should Exist    ${target_file}
        IF    ${copied_exists}
            Remove File    ${source_file}
            Log    Copied ${filename} to ${target_dir} and removed from source    level=INFO
        ELSE
            Fail    Failed to copy file to ${target_dir}
        END
    END

Click First Plus Icon With Fallback
    ${candidates}=    Create List    //table//tbody/tr[1]//i[contains(@class,'mdi-plus')]    //table//tbody/tr[1]//i[contains(@class,'fa-plus')]    //table//tbody/tr[1]//i[contains(@class,'icon-plus')]    /html/body/div/div/div[3]/form/div[2]/div[2]/table/tbody/tr[1]/td[10]/i
    FOR    ${xp}    IN    @{candidates}
        ${visible}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=${xp}    timeout=5s
        IF    ${visible}
            Scroll Element Into View    xpath=${xp}
            Wait Until Element Is Enabled    xpath=${xp}    timeout=2s
            Click Element    xpath=${xp}
            RETURN
        END
    END