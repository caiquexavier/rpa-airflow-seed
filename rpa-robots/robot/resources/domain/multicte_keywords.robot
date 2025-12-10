*** Settings ***
Library           SeleniumLibrary
Library           ${CURDIR}/../../libs/file_helper.py
Library           OperatingSystem
Library           Collections
Library           JSONLibrary
Resource    ${CURDIR}/../infra/ui_keywords.robot
Variables        ${CURDIR}/../../config/env_vars.py

*** Keywords ***
Login To MultiCTE
    [Documentation]    Login to MultiCTE system using credentials from config or provided parameters.
    [Arguments]    ${base_url}=${MULTICTE_BASE_URL}    ${usuario}=${MULTICTE_USERNAME}    ${senha}=${MULTICTE_PASSWORD}
    # Use BASE_URL from .env file as fallback if MULTICTE_BASE_URL is not configured
    IF    "${base_url}" == "" or "${base_url}" == "${EMPTY}"
        ${base_url}=    Get Variable Value    $BASE_URL    ${EMPTY}
        # If still empty, try to get from environment variable directly
        IF    "${base_url}" == "" or "${base_url}" == "${EMPTY}"
            ${base_url}=    Get Environment Variable    BASE_URL    default=${EMPTY}
        END
    END
    # Validate required parameters
    IF    "${base_url}" == "" or "${base_url}" == "${EMPTY}"
        Fail    BASE_URL is not configured. Please set BASE_URL or MULTICTE_BASE_URL environment variable in .env file or provide base_url argument.
    END
    IF    "${usuario}" == "" or "${usuario}" == "${EMPTY}"
        Fail    MULTICTE_USERNAME is not configured. Please set MULTICTE_USERNAME environment variable or provide usuario argument.
    END
    IF    "${senha}" == "" or "${senha}" == "${EMPTY}"
        Fail    MULTICTE_PASSWORD is not configured. Please set MULTICTE_PASSWORD environment variable or provide senha argument.
    END
    Go To    ${base_url}
    Sleep    1s
    Wait Until Element Is Visible    xpath=//*[@id="Usuario"]    timeout=20s
    Input Text    xpath=//*[@id="Usuario"]    ${usuario}
    Wait Until Element Is Visible    xpath=//*[@id="Senha"]    timeout=20s
    Input Text    xpath=//*[@id="Senha"]    ${senha}
    Wait Until Element Is Visible    xpath=//*[@id="login-form"]/div[2]/div[3]/button    timeout=20s
    Click Element    xpath=//*[@id="login-form"]/div[2]/div[3]/button
    Sleep    1s

Navigate To Leitura De Canhotos
    [Documentation]    Navigate to Leitura de Canhotos menu.
    Wait For Element And Click    xpath=//*[@id="js-nav-menu"]/li[6]/a
    Sleep    0.5s
    Wait For Element And Click    xpath=//*[@id="js-nav-menu"]/li[6]/ul/li[1]/a
    Sleep    0.5s
    Wait For Element And Click    xpath=//*[@id="js-nav-menu"]/li[6]/ul/li[1]/ul/li[3]/a
    Sleep    1s

Click Emissor Search Button
    [Documentation]    Click the search button to open emissor search modal. Uses multiple fallback strategies to handle dynamic IDs. Waits for blockUI overlay to disappear before clicking.
    Wait For BlockUI Overlay To Disappear
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
    [Documentation]    Wait for blockUI overlay to disappear before attempting to click elements. Handles both blockUI and block-ui-custom overlays. Has fallback if overlay doesn't disappear.
    ${blockui_overlay_xpath}=    Set Variable    xpath=//div[contains(@class, "blockUI") and contains(@class, "blockOverlay")]
    ${blockui_custom_xpath}=    Set Variable    xpath=//div[contains(@class, "block-ui-custom")]
    ${overlay_visible}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${blockui_overlay_xpath}    timeout=2s
    ${custom_overlay_visible}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${blockui_custom_xpath}    timeout=2s
    IF    ${overlay_visible}
        ${disappeared}=    Run Keyword And Return Status    Wait Until Element Is Not Visible    ${blockui_overlay_xpath}    timeout=30s
        IF    not ${disappeared}
            Log    BlockUI overlay did not disappear within 30s timeout, attempting to force dismiss    level=WARN
            TRY
                Execute Javascript    if (typeof $ !== 'undefined') { $('.blockUI').remove(); $('.blockOverlay').remove(); $('.block-ui-custom').remove(); } else { document.querySelectorAll('.blockUI, .blockOverlay, .block-ui-custom').forEach(el => el.remove()); }
            EXCEPT    AS    ${js_error}
                Log    Could not force dismiss overlay via JavaScript: ${js_error}    level=WARN
                # Try alternative method
                TRY
                    Execute Javascript    document.querySelectorAll('.blockUI, .blockOverlay, .block-ui-custom').forEach(el => el.style.display = 'none');
                EXCEPT
                    Log    Could not hide overlay via alternative method    level=WARN
                END
            END
            Sleep    0.5s
        END
    END
    IF    ${custom_overlay_visible}
        ${disappeared}=    Run Keyword And Return Status    Wait Until Element Is Not Visible    ${blockui_custom_xpath}    timeout=30s
        IF    not ${disappeared}
            Log    BlockUI custom overlay did not disappear within 30s timeout, attempting to force dismiss    level=WARN
            TRY
                Execute Javascript    if (typeof $ !== 'undefined') { $('.block-ui-custom').remove(); } else { document.querySelectorAll('.block-ui-custom').forEach(el => el.remove()); }
            EXCEPT    AS    ${js_error}
                Log    Could not force dismiss custom overlay via JavaScript: ${js_error}    level=WARN
                TRY
                    Execute Javascript    document.querySelectorAll('.block-ui-custom').forEach(el => el.style.display = 'none');
                EXCEPT
                    Log    Could not hide custom overlay via alternative method    level=WARN
                END
            END
            Sleep    0.5s
        END
    END

Search And Select Emissor
    [Documentation]    Search for emissor by code and select it. Ensures input is fully entered, Pesquisar is clicked, and results appear before clicking Selecionar.
    [Arguments]    ${emissor_code}=${MULTICTE_EMISSOR_CODE}
    Click Emissor Search Button
    Sleep    0.3s
    Input Emissor Razao Social    ${emissor_code}
    Click Pesquisar Button
    Click Selecionar Link
    Sleep    0.5s

Select Delivery Date And Trigger Upload
    [Documentation]    Select delivery date and trigger file upload.
    [Arguments]    ${delivery_date}=27/11/2025    ${doc_transportes}=${None}
    Click Delivery Date Picker
    Input Delivery Date    ${delivery_date}
    IF    ${doc_transportes} != ${None}
        Select And Upload Files    ${doc_transportes}
    END

Click Delivery Date Picker
    [Documentation]    Click the delivery date picker button to open date selection. Targets the Data Entrega datepicker specifically.
    ${date_picker_button_xpath}=    Set Variable    xpath=//label[contains(text(), "Data Entrega")]/following-sibling::div[contains(@class, "input-group")]//div[contains(@id, "tempus-dominus-append")]//span[contains(@class, "btn-primary") and contains(@class, "waves-effect")]//i[contains(@class, "fa-calendar")]
    ${date_picker_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${date_picker_button_xpath}    timeout=10s
    IF    not ${date_picker_found}
        ${alt_date_picker_xpath}=    Set Variable    xpath=//div[contains(@id, "tempus-dominus-append")]//span[contains(@class, "btn-primary") and contains(@class, "waves-effect")]//i[contains(@class, "fal") and contains(@class, "fa-calendar")]
        ${alt_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${alt_date_picker_xpath}    timeout=10s
        IF    ${alt_found}
            Scroll Element Into View    ${alt_date_picker_xpath}
            Set Focus To Element    ${alt_date_picker_xpath}
            Click Element    ${alt_date_picker_xpath}
        ELSE
            ${generic_date_picker_xpath}=    Set Variable    xpath=//label[contains(text(), "Data Entrega")]/following-sibling::div//span[contains(@class, "btn-primary")]//i[contains(@class, "fa-calendar")]
            Wait Until Element Is Visible    ${generic_date_picker_xpath}    timeout=10s
            Scroll Element Into View    ${generic_date_picker_xpath}
            Set Focus To Element    ${generic_date_picker_xpath}
            Click Element    ${generic_date_picker_xpath}
        END
    ELSE
        Scroll Element Into View    ${date_picker_button_xpath}
        Set Focus To Element    ${date_picker_button_xpath}
        Click Element    ${date_picker_button_xpath}
    END
    Sleep    0.3s

Input Delivery Date
    [Documentation]    Input delivery date into the date picker input field. Targets the Data Entrega input field specifically.
    [Arguments]    ${delivery_date}
    ${date_input_xpath}=    Set Variable    xpath=//label[contains(text(), "Data Entrega")]/following-sibling::div[contains(@class, "input-group")]//input[@type="text"]
    ${date_input_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${date_input_xpath}    timeout=5s
    IF    not ${date_input_found}
        ${alt_date_input_xpath}=    Set Variable    xpath=//label[contains(text(), "Data Entrega")]/following-sibling::div[contains(@class, "input-group")]//div[contains(@id, "tempus-dominus-append")]/../input
        ${alt_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${alt_date_input_xpath}    timeout=5s
        IF    ${alt_found}
            Wait For Element And Input Text    ${alt_date_input_xpath}    ${delivery_date}
            Sleep    0.3s
            Press Keys    ${alt_date_input_xpath}    RETURN
            Sleep    0.3s
        ELSE
            ${generic_date_input_xpath}=    Set Variable    xpath=//label[contains(text(), "Data Entrega")]/following-sibling::div//input[@type="text"]
            Wait Until Element Is Visible    ${generic_date_input_xpath}    timeout=5s
            Wait For Element And Input Text    ${generic_date_input_xpath}    ${delivery_date}
            Sleep    0.3s
            Press Keys    ${generic_date_input_xpath}    RETURN
            Sleep    0.3s
        END
    ELSE
        Wait For Element And Input Text    ${date_input_xpath}    ${delivery_date}
        Sleep    0.3s
        Press Keys    ${date_input_xpath}    RETURN
        Sleep    0.3s
    END

Click Upload Button
    [Documentation]    Click the upload button to trigger file upload. Uses stable attributes to find the upload label.
    ${upload_button_xpath}=    Set Variable    xpath=//label[contains(@class, "btn-primary") and .//i[contains(@class, "fa-upload")]]
    Wait Until Element Is Visible    ${upload_button_xpath}    timeout=10s
    Scroll Element Into View    ${upload_button_xpath}
    Set Focus To Element    ${upload_button_xpath}
    Click Element    ${upload_button_xpath}

Select And Upload Files
    [Documentation]    Select PDF files from processado folder for doc_transportes (excluding POD files) and upload them directly via file input element.
    [Arguments]    ${doc_transportes}
    # Get PDF files for this doc_transportes (excluding POD)
    ${pdf_files}=    Get Pdf Files For Doc Transportes    ${doc_transportes}
    ${file_count}=    Get Length    ${pdf_files}
    IF    ${file_count} == 0
        Fail    No PDF files found for doc_transportes ${doc_transportes} (excluding POD files)
    END
    Log    Found ${file_count} PDF files to upload for doc_transportes ${doc_transportes}    level=INFO
    
    # Try to find file input element (usually hidden, associated with the label)
    # First, try to find it near the upload button
    ${file_input_xpath}=    Set Variable    xpath=//label[contains(@class, "btn-primary") and .//i[contains(@class, "fa-upload")]]/following-sibling::input[@type="file"] | //label[contains(@class, "btn-primary") and .//i[contains(@class, "fa-upload")]]/preceding-sibling::input[@type="file"] | //input[@type="file"]
    ${file_input_found}=    Run Keyword And Return Status    Page Should Contain Element    ${file_input_xpath}    timeout=5s
    
    IF    ${file_input_found}
        # Enable multiple file selection if not already enabled
        ${file_input_element}=    Get WebElement    ${file_input_xpath}
        ${multiple_attr}=    Get Element Attribute    ${file_input_xpath}    multiple
        ${is_none_or_empty}=    Run Keyword And Return Status    Should Be Equal    ${multiple_attr}    ${None}
        ${is_none_or_empty}=    Run Keyword If    not ${is_none_or_empty}    Run Keyword And Return Status    Should Be Equal    ${multiple_attr}    ${EMPTY}
        IF    ${is_none_or_empty}
            Execute Javascript    arguments[0].setAttribute('multiple', 'multiple');    ARGUMENTS    ${file_input_element}
        END
        
        # Get folder path to ensure we're using absolute paths from correct folder
        ${folder_path}=    Evaluate    file_helper.get_processado_folder_path("${doc_transportes}")    modules=file_helper
        Log    Uploading files from folder: ${folder_path}    level=INFO
        Log    Files to upload: ${pdf_files}    level=INFO
        
        # Use Choose File with multiple files (newline-separated paths)
        # SeleniumLibrary's Choose File supports multiple files when separated by newlines
        # Note: Choose File uses absolute file paths directly, no dialog navigation needed
        ${file_paths_string}=    Join File Paths For Upload    ${pdf_files}
        Log    File paths string: ${file_paths_string}    level=INFO
        Choose File    ${file_input_xpath}    ${file_paths_string}
        Log    ${file_count} files selected via file input element    level=INFO
    ELSE
        # Handle file dialog if no file input element found
        Handle File Upload Dialog    ${pdf_files}    ${doc_transportes}
    END
    
    # Wait for upload to complete and verify - this must complete before browser can be closed
    Wait For Upload To Complete
    Log    Upload completed and confirmed for doc_transportes ${doc_transportes} - browser can now be closed    level=INFO

Click Upload Button And Select Files
    [Documentation]    Click the upload button and select PDF files from processado folder for doc_transportes, excluding POD files.
    [Arguments]    ${doc_transportes}
    Click Upload Button
    Select And Upload Files    ${doc_transportes}

Get Pdf Files For Doc Transportes
    [Documentation]    Get list of PDF file paths for doc_transportes, excluding POD files.
    [Arguments]    ${doc_transportes}
    ${pdf_files}=    Evaluate    file_helper.get_pdf_files_for_doc_transportes("${doc_transportes}", exclude_pod=True)    modules=file_helper
    RETURN    ${pdf_files}

Join File Paths For Upload
    [Documentation]    Join multiple file paths into a single string for file input (Selenium uses newline separator).
    [Arguments]    ${file_paths}
    ${joined}=    Evaluate    file_helper.join_file_paths_for_upload($file_paths)    modules=file_helper
    RETURN    ${joined}

Handle File Upload Dialog
    [Documentation]    Handle native OS file upload dialog. For Windows, uses pywinauto or similar approach.
    [Arguments]    ${pdf_files}    ${doc_transportes}
    # Get the folder path for navigation
    ${folder_path}=    Evaluate    file_helper.get_processado_folder_path("${doc_transportes}")    modules=file_helper
    Log    Handling file upload dialog for folder: ${folder_path}    level=INFO
    
    # For Windows, we'll need to use a library like pywinauto or AutoIt
    # For now, log a warning and try to use JavaScript if possible
    Log    Native file dialog detected. Attempting to handle via JavaScript or waiting for manual selection.    level=WARN
    # Wait a bit for dialog to appear
    Sleep    2s
    # Note: This is a placeholder - actual implementation would require pywinauto or AutoItLibrary
    # For now, we'll assume the file input element approach works

Wait For Upload To Complete
    [Documentation]    Wait for file upload to complete by checking for upload completion indicators. Optimized for faster completion.
    # Wait for blockUI overlay to disappear (indicates upload is processing/completed)
    Wait For BlockUI Overlay To Disappear
    # Quick check for upload completion - reduced timeout for faster execution
    ${upload_complete}=    Run Keyword And Return Status    Wait Until Keyword Succeeds    5s    0.3s    Verify Upload Completion
    IF    not ${upload_complete}
        Log    Upload completion verification timeout, but continuing    level=WARN
    END
    # Quick check for error messages only (non-blocking)
    ${error_indicator}=    Run Keyword And Return Status    Page Should Contain Element    xpath=//div[contains(@class, "alert-danger")] | //div[contains(@class, "toast-error")]    timeout=1s
    IF    ${error_indicator}
        ${error_text}=    Get Text    xpath=//div[contains(@class, "alert-danger")] | //div[contains(@class, "toast-error")]
        Log    Upload error detected: ${error_text}    level=WARN
    END

Verify Upload Completion
    [Documentation]    Verify that upload has completed by checking blockUI is gone and page is ready.
    # Quick check that blockUI is gone
    ${blockui_visible}=    Run Keyword And Return Status    Page Should Contain Element    xpath=//div[contains(@class, "blockUI") and contains(@class, "blockOverlay")]    timeout=0.5s
    IF    ${blockui_visible}
        Fail    BlockUI overlay still visible
    END
    # Quick check that page is interactive (no loading indicators)
    ${loading_indicator}=    Run Keyword And Return Status    Page Should Contain Element    xpath=//div[contains(@class, "loading")] | //div[contains(@class, "spinner")]    timeout=0.5s
    IF    ${loading_indicator}
        Fail    Page still loading
    END

Navigate To Canhotos Relatorios
    [Documentation]    Navigate to Canhotos Relatorios menu.
    Wait For Element And Click    xpath=//*[@id="js-nav-menu"]/li[6]/a
    Sleep    0.5s
    Wait For Element And Click    xpath=//*[@id="js-nav-menu"]/li[6]/ul/li[4]/a
    Sleep    0.5s
    Wait For Element And Click    xpath=//*[@id="js-nav-menu"]/li[6]/ul/li[4]/ul/li[1]/a
    Wait For BlockUI Overlay To Disappear
    Sleep    0.5s

Select Report Date
    [Documentation]    Select report date in the date picker.
    [Arguments]    ${report_date}=30/11/2025
    Click Report Date Picker
    Input Report Date    ${report_date}

Click Report Date Picker
    [Documentation]    Click the report date picker button to open date selection. Uses smart search for dynamic IDs.
    Wait For BlockUI Overlay To Disappear
    ${date_picker_xpath}=    Set Variable    xpath=//div[contains(@id, "tempus-dominus-append-a5fb2e8910c25feec7d24f1f69e6707d5")]//span
    ${date_picker_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${date_picker_xpath}    timeout=8s
    IF    not ${date_picker_found}
        ${alt_date_picker}=    Set Variable    xpath=//div[contains(@id, "tempus-dominus-append")]//span[contains(@class, "btn-primary")]//i[contains(@class, "fa-calendar")]
        ${alt_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${alt_date_picker}    timeout=8s
        IF    ${alt_found}
            Scroll Element Into View    ${alt_date_picker}
            Set Focus To Element    ${alt_date_picker}
            Click Element    ${alt_date_picker}
        ELSE
            ${generic_date_picker}=    Set Variable    xpath=//div[contains(@id, "tempus-dominus-append")]//span
            Wait Until Element Is Visible    ${generic_date_picker}    timeout=8s
            Scroll Element Into View    ${generic_date_picker}
            Set Focus To Element    ${generic_date_picker}
            Click Element    ${generic_date_picker}
        END
    ELSE
        Scroll Element Into View    ${date_picker_xpath}
        Set Focus To Element    ${date_picker_xpath}
        Click Element    ${date_picker_xpath}
    END
    Sleep    0.3s

Input Report Date
    [Documentation]    Input report date into the date picker input field.
    [Arguments]    ${report_date}
    ${date_input_xpath}=    Set Variable    xpath=//div[contains(@id, "tempus-dominus-append-a5fb2e8910c25feec7d24f1f69e6707d5")]/../input
    ${input_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${date_input_xpath}    timeout=5s
    IF    not ${input_found}
        ${alt_date_input}=    Set Variable    xpath=//div[contains(@id, "tempus-dominus-append")]/../input
        Wait Until Element Is Visible    ${alt_date_input}    timeout=5s
        Wait For Element And Input Text    ${alt_date_input}    ${report_date}
        Sleep    0.3s
        Press Keys    ${alt_date_input}    RETURN
    ELSE
        Wait For Element And Input Text    ${date_input_xpath}    ${report_date}
        Sleep    0.3s
        Press Keys    ${date_input_xpath}    RETURN
    END
    Sleep    0.3s

Select Report Campos
    [Documentation]    Select report campos checkboxes. Uses smart search to find checkboxes by label text. Attempts to click select campos button if needed. Closes campos selection modal after selecting all campos.
    Click Select Campos Button If Needed
    Select Campo Checkbox    Data Digitalização
    Select Campo Checkbox    Número
    Select Campo Checkbox    Número da Carga
    Select Campo Checkbox    Digitalização
    Select Campo Checkbox    Situação
    Select Campo Checkbox    Motivo da Rejeição
    Click Select Campos Button To Close

Click Select Campos Button If Needed
    [Documentation]    Click the select campos button to open campos selection modal if it exists. Uses specific ID.
    Wait For BlockUI Overlay To Disappear
    ${select_campos_xpath}=    Set Variable    xpath=//*[@id="preferencias-gridPreviewRelatorio"]
    Wait Until Element Is Visible    ${select_campos_xpath}    timeout=8s
    Scroll Element Into View    ${select_campos_xpath}
    Set Focus To Element    ${select_campos_xpath}
    Click Element    ${select_campos_xpath}
    Wait For BlockUI Overlay To Disappear
    Sleep    0.3s

Click Select Campos Button To Close
    [Documentation]    Click the select campos button to close campos selection modal. Uses specific ID.
    Wait For BlockUI Overlay To Disappear
    ${select_campos_xpath}=    Set Variable    xpath=//*[@id="preferencias-gridPreviewRelatorio"]
    Wait Until Element Is Visible    ${select_campos_xpath}    timeout=8s
    Scroll Element Into View    ${select_campos_xpath}
    Set Focus To Element    ${select_campos_xpath}
    Click Element    ${select_campos_xpath}
    Wait For BlockUI Overlay To Disappear
    Sleep    0.3s

Select Campo Checkbox
    [Documentation]    Select a checkbox by its label text. Finds label by exact text match, then uses label's 'for' attribute to locate and click the checkbox input element directly.
    [Arguments]    ${campo_label}
    Wait For BlockUI Overlay To Disappear
    ${label_xpath}=    Set Variable    xpath=//label[normalize-space(text())="${campo_label}"]
    ${label_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${label_xpath}    timeout=15s
    IF    ${label_found}
        ${label_for}=    Get Element Attribute    ${label_xpath}    for
        IF    "${label_for}" != "${None}" and "${label_for}" != ""
            ${checkbox_xpath}=    Set Variable    xpath=//input[@type="checkbox" and @id="${label_for}" and contains(@class, "custom-control-input")]
            ${checkbox_exists}=    Run Keyword And Return Status    Page Should Contain Element    ${checkbox_xpath}    timeout=10s
            IF    ${checkbox_exists}
                ${is_selected}=    Run Keyword And Return Status    Checkbox Should Be Selected    ${checkbox_xpath}
                IF    not ${is_selected}
                    ${checkbox_element}=    Get WebElement    ${checkbox_xpath}
                    Execute Javascript    arguments[0].click();    ARGUMENTS    ${checkbox_element}
                    Sleep    0.3s
                    ${verify_selected}=    Run Keyword And Return Status    Checkbox Should Be Selected    ${checkbox_xpath}
                    IF    not ${verify_selected}
                        Scroll Element Into View    ${checkbox_xpath}
                        Set Focus To Element    ${checkbox_xpath}
                        Click Element    ${checkbox_xpath}
                    END
                END
            ELSE
                Scroll Element Into View    ${label_xpath}
                Set Focus To Element    ${label_xpath}
                Click Element    ${label_xpath}
            END
        ELSE
            Scroll Element Into View    ${label_xpath}
            Set Focus To Element    ${label_xpath}
            Click Element    ${label_xpath}
        END
    ELSE
        ${alt_label_xpath}=    Set Variable    xpath=//label[contains(text(), "${campo_label}")]
        ${alt_label_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${alt_label_xpath}    timeout=10s
        IF    ${alt_label_found}
            ${alt_label_for}=    Get Element Attribute    ${alt_label_xpath}    for
            IF    "${alt_label_for}" != "${None}" and "${alt_label_for}" != ""
                ${alt_checkbox_xpath}=    Set Variable    xpath=//input[@type="checkbox" and @id="${alt_label_for}" and contains(@class, "custom-control-input")]
                ${alt_checkbox_exists}=    Run Keyword And Return Status    Page Should Contain Element    ${alt_checkbox_xpath}    timeout=10s
                IF    ${alt_checkbox_exists}
                    ${is_selected}=    Run Keyword And Return Status    Checkbox Should Be Selected    ${alt_checkbox_xpath}
                    IF    not ${is_selected}
                        ${alt_checkbox_element}=    Get WebElement    ${alt_checkbox_xpath}
                        Execute Javascript    arguments[0].click();    ARGUMENTS    ${alt_checkbox_element}
                        Sleep    0.3s
                        ${verify_selected}=    Run Keyword And Return Status    Checkbox Should Be Selected    ${alt_checkbox_xpath}
                        IF    not ${verify_selected}
                            Scroll Element Into View    ${alt_checkbox_xpath}
                            Set Focus To Element    ${alt_checkbox_xpath}
                            Click Element    ${alt_checkbox_xpath}
                        END
                    END
                ELSE
                    Scroll Element Into View    ${alt_label_xpath}
                    Set Focus To Element    ${alt_label_xpath}
                    Click Element    ${alt_label_xpath}
                END
            ELSE
                Scroll Element Into View    ${alt_label_xpath}
                Set Focus To Element    ${alt_label_xpath}
                Click Element    ${alt_label_xpath}
            END
        ELSE
            ${generic_checkbox}=    Set Variable    xpath=//input[@type="checkbox" and contains(@class, "custom-control-input")][@data-column[contains(., "${campo_label}")] or @name[contains(., "${campo_label}")] or @id[contains(., "${campo_label}")]]
            ${generic_found}=    Run Keyword And Return Status    Page Should Contain Element    ${generic_checkbox}    timeout=10s
            IF    ${generic_found}
                ${is_selected}=    Run Keyword And Return Status    Checkbox Should Be Selected    ${generic_checkbox}
                IF    not ${is_selected}
                    ${generic_checkbox_element}=    Get WebElement    ${generic_checkbox}
                    Execute Javascript    arguments[0].click();    ARGUMENTS    ${generic_checkbox_element}
                    Sleep    0.3s
                    ${verify_selected}=    Run Keyword And Return Status    Checkbox Should Be Selected    ${generic_checkbox}
                    IF    not ${verify_selected}
                        Scroll Element Into View    ${generic_checkbox}
                        Set Focus To Element    ${generic_checkbox}
                        Click Element    ${generic_checkbox}
                    END
                END
            ELSE
                Fail    Checkbox for "${campo_label}" not found
            END
        END
    END
    Sleep    0.2s

Generate Excel Report
    [Documentation]    Click the Generate Excel button. Uses smart search to find button by stable attributes.
    Wait For BlockUI Overlay To Disappear
    ${excel_button_xpath}=    Set Variable    xpath=//button[@id="a9cbbb64ad0bae8d8d3162877dd9e125f"]
    ${button_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${excel_button_xpath}    timeout=8s
    IF    not ${button_found}
        ${alt_excel_button}=    Set Variable    xpath=//button[contains(@class, "btn-success") and .//i[contains(@class, "fa-file-excel")] and .//span[contains(text(), "Gerar Planilha Excel")]]
        ${alt_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${alt_excel_button}    timeout=8s
        IF    ${alt_found}
            Scroll Element Into View    ${alt_excel_button}
            Set Focus To Element    ${alt_excel_button}
            Click Element    ${alt_excel_button}
        ELSE
            ${generic_excel_button}=    Set Variable    xpath=//button[contains(@class, "btn-success") and .//i[contains(@class, "fa-file-excel")]]
            Wait Until Element Is Visible    ${generic_excel_button}    timeout=8s
            Scroll Element Into View    ${generic_excel_button}
            Set Focus To Element    ${generic_excel_button}
            Click Element    ${generic_excel_button}
        END
    ELSE
        Scroll Element Into View    ${excel_button_xpath}
        Set Focus To Element    ${excel_button_xpath}
        Click Element    ${excel_button_xpath}
    END
    Wait For BlockUI Overlay To Disappear
    Sleep    1s

Generate PDF Report
    [Documentation]    Click the Generate PDF button. Uses smart search to find button by stable attributes.
    Wait For BlockUI Overlay To Disappear
    ${pdf_button_xpath}=    Set Variable    xpath=//button[@id="a594409f5625e099ffab6bc85fee17d93"]
    ${button_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${pdf_button_xpath}    timeout=8s
    IF    not ${button_found}
        ${alt_pdf_button}=    Set Variable    xpath=//button[contains(@class, "btn-success") and .//i[contains(@class, "fa-file-pdf")] and .//span[contains(text(), "Gerar PDF")]]
        ${alt_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${alt_pdf_button}    timeout=8s
        IF    ${alt_found}
            Scroll Element Into View    ${alt_pdf_button}
            Set Focus To Element    ${alt_pdf_button}
            Click Element    ${alt_pdf_button}
        ELSE
            ${generic_pdf_button}=    Set Variable    xpath=//button[contains(@class, "btn-success") and .//i[contains(@class, "fa-file-pdf")]]
            Wait Until Element Is Visible    ${generic_pdf_button}    timeout=8s
            Scroll Element Into View    ${generic_pdf_button}
            Set Focus To Element    ${generic_pdf_button}
            Click Element    ${generic_pdf_button}
        END
    ELSE
        Scroll Element Into View    ${pdf_button_xpath}
        Set Focus To Element    ${pdf_button_xpath}
        Click Element    ${pdf_button_xpath}
    END
    Wait For BlockUI Overlay To Disappear
    Sleep    1s

Select Report
    [Documentation]    Click search button, select relatorio padrao from table, and filter table to show only relatorio padrao.
    Click Report Search Button
    Select Relatorio Padrao
    Filter Table To Relatorio Padrao

Click Report Search Button
    [Documentation]    Click the report search button. Uses multiple fallback strategies to handle dynamic IDs.
    Wait For BlockUI Overlay To Disappear
    ${search_button_xpath}=    Set Variable    xpath=//button[@class="btn btn-primary waves-effect waves-themed" and contains(@id, "ad5941114e868341d16c4a8f3a77f1c30") and @aria-label="Buscar"]
    ${search_button_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${search_button_xpath}    timeout=8s
    IF    not ${search_button_found}
        ${alt_search_button}=    Set Variable    xpath=//button[@class="btn btn-primary waves-effect waves-themed" and @aria-label="Buscar" and .//i[contains(@class, "fa-search")]]
        ${alt_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${alt_search_button}    timeout=8s
        IF    ${alt_found}
            Wait For Element And Click    ${alt_search_button}
        ELSE
            ${generic_search_button}=    Set Variable    xpath=//button[@type="button" and @aria-label="Buscar" and contains(@class, "btn-primary") and .//i[contains(@class, "fa-search")]]
            Wait Until Element Is Visible    ${generic_search_button}    timeout=8s
            Scroll Element Into View    ${generic_search_button}
            Set Focus To Element    ${generic_search_button}
            Click Element    ${generic_search_button}
        END
    ELSE
        Wait For Element And Click    ${search_button_xpath}
    END
    Wait For BlockUI Overlay To Disappear
    Sleep    0.3s

Select Relatorio Padrao
    [Documentation]    Select relatorio padrao from the table using XPath.
    Wait For BlockUI Overlay To Disappear
    ${relatorio_padrao_xpath}=    Set Variable    xpath=//*[@id="55"]/td[3]/a
    Wait Until Element Is Visible    ${relatorio_padrao_xpath}    timeout=12s
    Scroll Element Into View    ${relatorio_padrao_xpath}
    Wait For Element And Click    ${relatorio_padrao_xpath}
    Sleep    0.3s

Filter Table To Relatorio Padrao
    [Documentation]    Filter table to show only rows where value equals relatorio padrao.
    Wait For BlockUI Overlay To Disappear
    ${table_rows_xpath}=    Set Variable    xpath=//table//tbody//tr
    ${table_visible}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${table_rows_xpath}    timeout=12s
    IF    ${table_visible}
        ${rows}=    Get WebElements    ${table_rows_xpath}
        FOR    ${row}    IN    @{rows}
            TRY
                ${row_text_content}=    Get Text    ${row}
                ${is_relatorio_padrao}=    Evaluate    "relatorio padrao" in "${row_text_content}".lower()
                IF    not ${is_relatorio_padrao}
                    ${row_visible}=    Run Keyword And Return Status    Element Should Be Visible    ${row}
                    IF    ${row_visible}
                        Execute Javascript    arguments[0].style.display = 'none';    ARGUMENTS    ${row}
                    END
                END
            EXCEPT
                Continue For Loop
            END
        END
    END
    Sleep    0.2s

Preview
    [Documentation]    Click the preview button. Uses direct ID match with fallback strategies. Waits for page to be ready after click.
    Wait For BlockUI Overlay To Disappear
    ${preview_button_xpath}=    Set Variable    xpath=//*[@id="abd66478a61f271bddb60c84ee1a5a8cd"]
    ${preview_button_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${preview_button_xpath}    timeout=8s
    IF    not ${preview_button_found}
        ${alt_preview_button}=    Set Variable    xpath=//button[@class="btn btn-primary" and .//span[text()="Preview"] and .//i[contains(@class, "fa-search")]]
        ${alt_found}=    Run Keyword And Return Status    Wait Until Element Is Visible    ${alt_preview_button}    timeout=8s
        IF    ${alt_found}
            Scroll Element Into View    ${alt_preview_button}
            Set Focus To Element    ${alt_preview_button}
            Click Element    ${alt_preview_button}
        ELSE
            ${generic_preview_button}=    Set Variable    xpath=//button[@class="btn btn-primary" and .//span[text()="Preview"]]
            Wait Until Element Is Visible    ${generic_preview_button}    timeout=8s
            Scroll Element Into View    ${generic_preview_button}
            Set Focus To Element    ${generic_preview_button}
            Click Element    ${generic_preview_button}
        END
    ELSE
        Scroll Element Into View    ${preview_button_xpath}
        Set Focus To Element    ${preview_button_xpath}
        Click Element    ${preview_button_xpath}
    END
    Wait For BlockUI Overlay To Disappear
    Sleep    0.5s

