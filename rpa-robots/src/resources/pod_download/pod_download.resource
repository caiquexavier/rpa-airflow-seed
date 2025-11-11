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

*** Keywords ***
Load JSON Data
    [Arguments]    ${json_string}
    Log    Received JSON string: ${json_string}
    
    # Check if json_string is empty or invalid
    ${is_empty}=    Run Keyword And Return Status    Should Be Equal    ${json_string}    ${EMPTY}
    IF    ${is_empty}
        Log    No JSON data provided; nothing to process
        Set Global Variable    ${JSON_DATA}    {"rpa_request": {"notas_fiscais": []}}
        RETURN
    END
    
    # Check if json_string is already a dict or needs to be parsed
    ${is_dict}=    Run Keyword And Return Status    Should Be Equal    ${json_string.__class__.__name__}    dict
    IF    ${is_dict}
        Set Global Variable    ${JSON_DATA}    ${json_string}
        Log    Loaded JSON data (already parsed): ${json_string}
    ELSE
        TRY
            ${json_data}=    Convert String To Json    ${json_string}
            Set Global Variable    ${JSON_DATA}    ${json_data}
            Log    Loaded JSON data (parsed from string): ${json_data}
        EXCEPT    AS    ${error}
            Log    Error parsing JSON: ${error}
            Log    Falling back to empty notas_fiscais list
            Set Global Variable    ${JSON_DATA}    {"rpa_request": {"notas_fiscais": []}}
        END
    END

Process Nota Fiscal Array
    Initialize Error Results
    # Get the nota_fiscal array from rpa_request.nota_fiscal using [*] to get individual elements
    ${nota_fiscal_array}=    Get Value From Json    ${JSON_DATA}    $.rpa_request.notas_fiscais[*]
    Log    Raw nota_fiscal_array: ${nota_fiscal_array}
    # Check if we got a valid array
    ${array_length}=    Get Length    ${nota_fiscal_array}
    Log    Array length: ${array_length} (strict execution)
    
    IF    ${array_length} > 0
        Log    Processing ${array_length} Nota Fiscal values (strict execution)
        ${processed_count}=    Set Variable    0
        FOR    ${index}    IN RANGE    0    ${array_length}
            ${current_nota_fiscal}=    Get Value From Json    ${JSON_DATA}    $.rpa_request.notas_fiscais[${index}]
            Log    Processing Nota Fiscal ${index + 1}/${array_length}: ${current_nota_fiscal[0]}
            Process Single Nota Fiscal    ${current_nota_fiscal[0]}
            ${processed_count}=    Evaluate    ${processed_count} + 1
            Log    Completed ${processed_count}/${array_length} Nota Fiscal items
        END
        Log    Finished processing all ${array_length} Nota Fiscal items
    ELSE
        Log    No notas_fiscais provided; skipping processing
    END
    Build Response Message
    

Process Nota Fiscal Array From Variables
    Initialize Error Results
    # Check if we have the rpa_request variable (from variable file)
    ${has_rpa_request}=    Run Keyword And Return Status    Variable Should Exist    ${rpa_request}
    IF    ${has_rpa_request}
        Log    Processing Nota Fiscal array from rpa_request variable
        Log    rpa_request content: ${rpa_request}
        # Get the notas_fiscais array directly from rpa_request
        ${notas_fiscais}=    Get Value From Json    ${rpa_request}    $.notas_fiscais
        Log    Raw notas_fiscais from JSON: ${notas_fiscais}
        # Extract the actual array (JSONLibrary returns list of matches)
        ${outer_len}=    Get Length    ${notas_fiscais}
        Log    Outer length: ${outer_len}
        IF    ${outer_len} > 0
            ${actual_array}=    Set Variable    ${notas_fiscais[0]}
            Log    Actual array extracted: ${actual_array}
        ELSE
            ${actual_array}=    Create List
            Log    Empty array, creating empty list
        END
        ${array_length}=    Get Length    ${actual_array}
        Log    Array length: ${array_length} (strict execution - will process exactly ${array_length} items)
        
        IF    ${array_length} > 0
            ${processed_count}=    Set Variable    0
            ${success_count}=    Set Variable    0
            ${error_count}=    Set Variable    0
            
            # Process exactly array_length items, no more, no less
            # Loop stays in Registro de Canhotos menu, only downloads NF files
            FOR    ${index}    IN RANGE    0    ${array_length}
                # Safety check: ensure we don't exceed array length
                IF    ${index} >= ${array_length}
                    Log    Safety check: Index ${index} exceeds array length ${array_length}, stopping loop
                    Exit For Loop
                END
                ${current_nota_fiscal}=    Set Variable    ${actual_array[${index}]}
                Log    [${index + 1}/${array_length}] Processing Nota Fiscal: ${current_nota_fiscal}
                TRY
                    Process Single Nota Fiscal    ${current_nota_fiscal}
                    ${success_count}=    Evaluate    ${success_count} + 1
                    Log    [${index + 1}/${array_length}] Successfully processed: ${current_nota_fiscal}
                EXCEPT    AS    ${error}
                    ${error_count}=    Evaluate    ${error_count} + 1
                    Append Error Result    ${current_nota_fiscal}    ${error}
                    Log    [${index + 1}/${array_length}] Error processing ${current_nota_fiscal}: ${error}
                END
                ${processed_count}=    Evaluate    ${processed_count} + 1
                Log    Progress: ${processed_count}/${array_length} items completed
            END
            
            # Build execution log
            Log    ===== EXECUTION SUMMARY =====
            Log    Total items in array: ${array_length}
            Log    Processed: ${processed_count}
            Log    Successful: ${success_count}
            Log    Errors: ${error_count}
            Log    ============================
        ELSE
            Log    Empty notas_fiscais array; nothing to process
        END
    ELSE
        Log    No rpa_request variable found; skipping processing
    END
    Build Response Message

Process Single Nota Fiscal
    [Arguments]    ${nota_fiscal}
    Log    Processing Nota Fiscal: ${nota_fiscal}
    Input Nota Fiscal And Search    ${nota_fiscal}

Login To e-Cargo
    [Arguments]    ${base_url}=${BASE_URL}
    Go To    ${base_url}
    Wait Until Element Is Visible    css=#email    timeout=15s
    Input Text    css=#email    ${USUARIO}
    Wait Until Element Is Visible    css=#password    timeout=15s
    Input Text    css=#password    ${SENHA}
    Wait Until Element Is Enabled    css=#login    timeout=15s
    Click Element    css=#login
    Sleep    1.5s

Open Operacional Menu
    Wait Until Element Is Visible    xpath=//*[contains(text(),'Operacional')]    timeout=10s
    Click Element    xpath=//*[contains(text(),'Operacional')]
    Sleep    1s

Open Registro De Canhotos Submenu
    Wait Until Element Is Visible    xpath=//div[@class='v-list__tile__title' and text()='Registro de Canhotos']    timeout=10s
    Click Element    xpath=//div[@class='v-list__tile__title' and text()='Registro de Canhotos']
    Sleep    2s

Input Nota Fiscal And Search
    [Arguments]    ${nota_fiscal}=${NOTA_FISCAL}
    # Ensure we're in the frame for Registro de Canhotos
    Wait Until Element Is Visible    css=iframe#frame    timeout=15s
    Select Frame    css=iframe#frame
    # Clear previous search and input new NF
    Wait Until Element Is Visible    css=input[name="txtNotaFiscal"]    timeout=15s
    Click Element    css=input[name="txtNotaFiscal"]
    Clear Element Text    css=input[name="txtNotaFiscal"]
    Input Text    css=input[name="txtNotaFiscal"]    ${nota_fiscal}
    # Click on Pesquisar button
    Wait Until Element Is Visible    xpath=/html/body/div/div/div[3]/form/div[1]/div[6]/div/div[1]/button    timeout=10s
    Click Element    xpath=/html/body/div/div/div[3]/form/div[1]/div[6]/div/div[1]/button
    Sleep    1s
    # Check for error modal after search
    ${has_error_modal}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=//*[@id="modalMensagem"]/div/div/div    timeout=3s
    IF    ${has_error_modal}
        ${error_msg}=    Get Text    xpath=//*[@id="modalMensagem"]/div/div/div/div[1]
        Log    Error modal detected after search: ${error_msg}
        Append Error Result    ${nota_fiscal}    ${error_msg}
        Click Element    xpath=//*[@id="modalMensagem"]/div/div/div/div[2]/button
        Sleep    1s
        Unselect Frame
        RETURN
    END
    # Click on "+" button to expand row
    Click First Plus Icon With Fallback
    # Wait for the expanded row content to be visible instead of fixed sleep
    Wait Until Element Is Visible    xpath=/html/body/div/div/div[3]/form/div[2]/div[2]/table/tbody/tr[2]/td/div/div[2]/div[3]/button    timeout=5s
    # Click on Canhoto NF button
    Click Element    xpath=/html/body/div/div/div[3]/form/div[2]/div[2]/table/tbody/tr[2]/td/div/div[2]/div[3]/button
    Sleep    1s
    # Check for error modal
    ${has_error_modal}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=//*[@id="modalMensagem"]/div/div/div    timeout=3s
    IF    ${has_error_modal}
        ${error_msg}=    Get Text    xpath=//*[@id="modalMensagem"]/div/div/div/div[1]
        Log    Error modal detected: ${error_msg}
        Append Error Result    ${nota_fiscal}    ${error_msg}
        Click Element    xpath=//*[@id="modalMensagem"]/div/div/div/div[2]/button
        Sleep    1s
        Unselect Frame
        RETURN
    END
    # Wait for Canhoto modal and download PDFs
    Wait Until Element Is Visible    xpath=//*[@id="ModalCanhotoNf"]    timeout=10s
    Download All PDF Files
    Sleep    0.5s
    # Close modal and return to search screen
    ${close_button}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=//*[@id="ModalCanhotoNf"]//button[contains(@class,'close') or contains(@ng-click,'close')]    timeout=2s
    IF    ${close_button}
        Click Element    xpath=//*[@id="ModalCanhotoNf"]//button[contains(@class,'close') or contains(@ng-click,'close')]
    END
    Unselect Frame

Initialize Error Results
    Set Global Variable    ${ERROR_RESULTS}    ${EMPTY}
    ${list}=    Create List
    Set Global Variable    ${ERROR_RESULTS}    ${list}

Append Error Result
    [Arguments]    ${nota_fiscal}    ${message}
    ${entry}=    Create Dictionary    nota_fiscal=${nota_fiscal}    message=${message}
    Append To List    ${ERROR_RESULTS}    ${entry}

Build Response Message
    # Build simple execution log response
    ${error_count}=    Get Length    ${ERROR_RESULTS}
    ${has_errors}=    Evaluate    ${error_count} > 0
    IF    ${has_errors}
        ${log_message}=    Set Variable    Execution completed with ${error_count} error(s). Check errors for details.
    ELSE
        ${log_message}=    Set Variable    Execution completed successfully.
    END
    ${response}=    Create Dictionary    log=${log_message}    errors=${ERROR_RESULTS}    error_count=${error_count}
    ${response_str}=    Convert To String    ${response}
    Set Global Variable    ${RESULT_MESSAGE}    ${response_str}
    Log    Response message: ${response_str}

Download All PDF Files
    # Get count of all PDF download buttons in the modal
    ${pdf_buttons_count}=    Get Element Count    xpath=//*[@id="ModalCanhotoNf"]//button[contains(@ng-click, 'buscarArquivo') and contains(., 'Pdf')]
    Log    Found ${pdf_buttons_count} PDF download buttons
    
    # Get download directory path
    ${base_path}=    Join Path    ${CURDIR}    ..    ..    ..
    ${download_dir}=    Join Path    ${base_path}    assets    download
    ${download_dir}=    Normalize Path    ${download_dir}
    ${download_dir_exists}=    Run Keyword And Return Status    Directory Should Exist    ${download_dir}
    IF    not ${download_dir_exists}
        Create Directory    ${download_dir}
    END
    
    # Loop through all PDF buttons and click them
    FOR    ${index}    IN RANGE    1    ${pdf_buttons_count} + 1
        ${button_xpath}=    Set Variable    (//*[@id="ModalCanhotoNf"]//button[contains(@ng-click, 'buscarArquivo') and contains(., 'Pdf')])[${index}]
        Wait Until Element Is Visible    xpath=${button_xpath}    timeout=5s
        ${is_enabled}=    Run Keyword And Return Status    Element Should Be Enabled    xpath=${button_xpath}
        IF    ${is_enabled}
            Log    Clicking PDF download button ${index}
            # Get list of existing PDF files before download
            ${existing_files_str}=    Evaluate    set([f for f in os.listdir(r"${download_dir}") if f.endswith('.pdf')])    os
            Log    Existing PDF files before download: ${existing_files_str}
            Click Element    xpath=${button_xpath}
            # Wait for download to complete - wait for new file to appear and stabilize
            Wait For Download To Complete    ${download_dir}    ${existing_files_str}    timeout=30s
        ELSE
            Log    PDF download button ${index} is disabled, skipping
        END
    END

Wait For Download To Complete
    [Arguments]    ${download_dir}    ${existing_files_set}    ${timeout}=30s
    # Wait for a new PDF file to appear and stabilize (download complete)
    ${timeout_seconds}=    Evaluate    int('${timeout}'.replace('s', '')) if 's' in '${timeout}' else int('${timeout}')
    ${max_iterations}=    Evaluate    ${timeout_seconds} * 2    # Check every 0.5s
    ${new_file_found}=    Set Variable    ${False}
    ${stable_file}=    Set Variable    ${None}
    ${stable_size}=    Set Variable    ${0}
    
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
                ${stable_file}=    Set Variable    ${latest_file}
                ${stable_size}=    Set Variable    ${current_size}
                BREAK
            END
        END
        Sleep    0.5s
    END
    
    IF    not ${new_file_found}
        ${all_files_set}=    Evaluate    set([f for f in os.listdir(r"${download_dir}") if f.endswith('.pdf')])    os
        Log    WARNING: No new PDF file detected after ${timeout}
        Log    Existing files: ${existing_files_set}
        Log    Current files: ${all_files_set}
        Fail    Download timeout: No new PDF file appeared in ${download_dir} within ${timeout}
    END
    
    Log    Download complete: ${stable_file} (${stable_size} bytes)

Click First Plus Icon With Fallback
    # Try multiple candidate locators for the "+" expand icon and click the first visible one
    ${candidates}=    Create List    //table//tbody/tr[1]//i[contains(@class,'mdi-plus')]    //table//tbody/tr[1]//i[contains(@class,'fa-plus')]    //table//tbody/tr[1]//i[contains(@class,'icon-plus')]    /html/body/div/div/div[3]/form/div[2]/div[2]/table/tbody/tr[1]/td[10]/i
    FOR    ${xp}    IN    @{candidates}
        ${visible}=    Run Keyword And Return Status    Wait Until Element Is Visible    xpath=${xp}    timeout=5s
        IF    ${visible}
            Scroll Element Into View    xpath=${xp}
            Wait Until Element Is Enabled    xpath=${xp}    timeout=2s
            Click Element    xpath=${xp}
            Exit For Loop If    ${True}
        END
    END
    # If none matched, log and continue (no hard failure)
    Log    Plus icon not found or not visible; continuing without expanding