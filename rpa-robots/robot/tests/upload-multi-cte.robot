*** Settings ***
Resource    ${CURDIR}/../resources/infra/browser_keywords.robot
Resource    ${CURDIR}/../resources/domain/multicte_keywords.robot
Resource    ${CURDIR}/../resources/saga/saga_context_keywords.robot
Library           ${CURDIR}/../libs/saga_client.py
Library           ${CURDIR}/../libs/file_helper.py
Library           JSONLibrary
Library           Collections
Variables        ${CURDIR}/../variables/centro_access.py

Suite Setup    Initialize Test Suite
Suite Teardown    Cleanup Screenshots
Test Setup    Configure Screenshot Directory

*** Variables ***
# Default fallback doc_transportes_list when saga is not present
# This matches DEFAULT_DOC_TRANSPORTES_LIST from gpt_pdf_extractor_operator.py

*** Test Cases ***
Upload Multi CTE For Emissor
    [Documentation]    Upload Multi CTE files for each subfolder in aprovados directory.
    ...                Each subfolder name is treated as doc_transportes ID.
    ...                Matches folder name with saga data to get centro_distribuicao.
    ...                Each doc_transportes entry is processed in a separate browser session.
    ...                Skips rejeitados and Nao processados folders.
    ${doc_transportes_list}=    Get Doc Transportes List From Aprovados
    Should Not Be Empty    ${doc_transportes_list}    Nenhum subfolder encontrado em aprovados
    
    ${response_list}=    Process All Doc Transportes Entries    ${doc_transportes_list}
    ${final_response}=    Create Dictionary    doc_transportes_list=${response_list}
    Finish Saga Execution    ${final_response}

*** Keywords ***
Initialize Test Suite
    [Documentation]    Initialize test suite: configure screenshots to save in results folder.
    Configure Screenshot Directory

Get Doc Transportes List From Aprovados
    [Documentation]    Get doc_transportes_list from aprovados subfolders, matching with saga data to get centro_distribuicao.
    ...                Each subfolder name in aprovados is treated as doc_transportes ID.
    ...                Uses fallback saga data if saga data is not available.
    ${aprovados_folders}=    Get Aprovados Subfolders
    Should Not Be Empty    ${aprovados_folders}    Nenhum subfolder encontrado em aprovados
    
    ${saga_data}=    Get Saga Data Variable
    ${saga_doc_list}=    Extract Doc Transportes List From Saga    ${saga_data}
    
    # Use fallback if saga data is not available or empty
    IF    ${saga_doc_list} == ${None}
        Log    Saga data não disponível. Usando fallback DEFAULT_DOC_TRANSPORTES_LIST.    level=INFO
        ${saga_doc_list}=    Create Default Doc Transportes List
    ELSE
        ${is_empty}=    Run Keyword And Return Status    Should Be Empty    ${saga_doc_list}
        IF    ${is_empty}
            Log    Saga data está vazia. Usando fallback DEFAULT_DOC_TRANSPORTES_LIST.    level=INFO
            ${saga_doc_list}=    Create Default Doc Transportes List
        END
    END
    
    ${doc_transportes_list}=    Create List
    FOR    ${folder_name}    IN    @{aprovados_folders}
        ${doc_entry}=    Create Doc Entry From Folder Name    ${folder_name}    ${saga_doc_list}
        IF    ${doc_entry} != ${None}
            Append To List    ${doc_transportes_list}    ${doc_entry}
            Log    Adicionado DOC ${folder_name} à lista de processamento    level=INFO
        ELSE
            Log    Não foi possível criar doc_entry para folder ${folder_name} - centro_distribuicao não encontrado na saga ou fallback    level=WARN
        END
    END
    
    RETURN    ${doc_transportes_list}

Get Aprovados Subfolders
    [Documentation]    Get list of subfolder names (doc_transportes IDs) from aprovados directory.
    ${subfolders}=    Evaluate    file_helper.get_aprovados_subfolders()    modules=file_helper
    ${count}=    Get Length    ${subfolders}
    Log    Encontrados ${count} subfolders em aprovados: ${subfolders}    level=INFO
    RETURN    ${subfolders}

Create Doc Entry From Folder Name
    [Arguments]    ${folder_name}    ${saga_doc_list}
    [Documentation]    Create doc_entry from folder name, matching with saga data (or fallback) to get centro_distribuicao.
    ...                Returns None if centro_distribuicao cannot be found in saga data or fallback.
    ...                Note: saga_doc_list should already be populated with fallback data if saga data was not available.
    IF    ${saga_doc_list} == ${None}
        Log    saga_doc_list é None - não é possível obter centro_distribuicao para ${folder_name}    level=WARN
        RETURN    ${None}
    END
    
    ${is_empty}=    Run Keyword And Return Status    Should Be Empty    ${saga_doc_list}
    IF    ${is_empty}
        Log    saga_doc_list está vazio - não é possível obter centro_distribuicao para ${folder_name}    level=WARN
        RETURN    ${None}
    END
    
    # Search for matching doc_transportes in saga data (or fallback)
    ${matched_entry}=    Find Doc Entry In Saga List    ${folder_name}    ${saga_doc_list}
    IF    ${matched_entry} == ${None}
        Log    DOC ${folder_name} não encontrado na saga data ou fallback - centro_distribuicao não disponível    level=WARN
        RETURN    ${None}
    END
    
    # Extract centro_distribuicao from matched entry
    ${has_centro}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${matched_entry}    centro_distribuicao
    IF    not ${has_centro}
        Log    centro_distribuicao não encontrado no entry da saga para DOC ${folder_name}    level=WARN
        RETURN    ${None}
    END
    
    ${centro_distribuicao}=    Get From Dictionary    ${matched_entry}    centro_distribuicao
    ${doc_entry}=    Create Dictionary    doc_transportes=${folder_name}    centro_distribuicao=${centro_distribuicao}
    
    # Optionally include nf_e if available
    ${has_nf_e}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${matched_entry}    nf_e
    IF    ${has_nf_e}
        ${nf_e}=    Get From Dictionary    ${matched_entry}    nf_e
        Set To Dictionary    ${doc_entry}    nf_e=${nf_e}
    END
    
    RETURN    ${doc_entry}

Find Doc Entry In Saga List
    [Arguments]    ${doc_transportes_id}    ${saga_doc_list}
    [Documentation]    Find doc_entry in saga doc_transportes_list matching the doc_transportes_id.
    FOR    ${entry}    IN    @{saga_doc_list}
        ${entry_doc_id}=    Get From Dictionary    ${entry}    doc_transportes
        IF    '${entry_doc_id}' == '${doc_transportes_id}'
            RETURN    ${entry}
        END
    END
    RETURN    ${None}

Get Doc Transportes List With Fallback
    [Documentation]    Get doc_transportes_list from saga data, or use default fallback if saga is not present.
    ...                DEPRECATED: Use Get Doc Transportes List From Aprovados instead.
    ${saga_data}=    Get Saga Data Variable
    ${doc_transportes_list}=    Extract Doc Transportes List From Saga    ${saga_data}
    
    IF    ${doc_transportes_list} == ${None}
        Log    Saga data not available. Using DEFAULT_DOC_TRANSPORTES_LIST fallback.    level=INFO
        ${doc_transportes_list}=    Create Default Doc Transportes List
    ELSE
        ${is_empty}=    Run Keyword And Return Status    Should Be Empty    ${doc_transportes_list}
        IF    ${is_empty}
            Log    Saga data is empty. Using DEFAULT_DOC_TRANSPORTES_LIST fallback.    level=INFO
            ${doc_transportes_list}=    Create Default Doc Transportes List
        END
    END
    
    RETURN    ${doc_transportes_list}

Get Saga Data Variable
    [Documentation]    Get saga data from $data variable.
    ${saga_data}=    Get Variable Value    $data    ${None}
    RETURN    ${saga_data}

Extract Doc Transportes List From Saga
    [Arguments]    ${saga_data}
    [Documentation]    Extract doc_transportes_list from saga data structure.
    IF    ${saga_data} == ${None}
        RETURN    ${None}
    END
    
    TRY
        ${parsed}=    Convert Saga Payload To Dict    ${saga_data}
        ${doc_transportes_list}=    Get Doc Transportes List From Parsed    ${parsed}
        IF    ${doc_transportes_list} != ${None}
            Log    Using doc_transportes_list from saga data    level=INFO
            RETURN    ${doc_transportes_list}
        END
    EXCEPT    AS    ${error}
        Log    Failed to parse saga data: ${error}. Using default fallback.    level=WARN
    END
    
    RETURN    ${None}

Get Doc Transportes List From Parsed
    [Arguments]    ${parsed}
    [Documentation]    Extract doc_transportes_list from parsed saga data.
    ${has_doc_list}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${parsed}    doc_transportes_list
    IF    ${has_doc_list}
        ${doc_transportes_list}=    Get From Dictionary    ${parsed}    doc_transportes_list
        RETURN    ${doc_transportes_list}
    END
    
    ${has_data_node}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${parsed}    data
    IF    ${has_data_node}
        ${data_node}=    Get From Dictionary    ${parsed}    data
        ${has_doc_list_in_data}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${data_node}    doc_transportes_list
        IF    ${has_doc_list_in_data}
            ${doc_transportes_list}=    Get From Dictionary    ${data_node}    doc_transportes_list
            RETURN    ${doc_transportes_list}
        END
    END
    
    RETURN    ${None}

Create Default Doc Transportes List
    [Documentation]    Create default doc_transportes_list matching DEFAULT_DOC_TRANSPORTES_LIST from gpt_pdf_extractor_operator.py.
    ${default_json}=    Set Variable    [{"doc_transportes": "96722724", "centro_distribuicao": "3031", "nf_e": ["4921184", "4921183", "4921190", "4921192", "4920188", "4941272", "4941187", "4941186", "4941177"]}, {"doc_transportes": "96802793", "centro_distribuicao": "3202", "nf_e": ["1301229", "1301232", "1301236", "1303468", "1301233", "1301231", "1301230", "1301234", "1301235", "1301228"]}, {"doc_transportes": "97542262", "centro_distribuicao": "3202", "nf_e": ["1319786", "1320038", "1329928", "1328276", "1328274", "1328260"]}]
    ${default_list}=    Convert String To Json    ${default_json}
    RETURN    ${default_list}

Convert Saga Payload To Dict
    [Arguments]    ${payload}
    [Documentation]    Convert saga payload to dictionary (handles both string and dict).
    ${is_string}=    Evaluate    isinstance(${payload}, str)
    IF    ${is_string}
        ${result}=    Convert String To Json    ${payload}
    ELSE
        ${result}=    Set Variable    ${payload}
    END
    RETURN    ${result}

Process All Doc Transportes Entries
    [Arguments]    ${doc_transportes_list}
    [Documentation]    Process all doc_transportes entries, each in a separate browser session.
    ${response_list}=    Create List
    FOR    ${doc_entry}    IN    @{doc_transportes_list}
        ${doc_response}=    Process Doc Transportes Entry With Browser    ${doc_entry}
        Append To List    ${response_list}    ${doc_response}
        ${doc_id}=    Get From Dictionary    ${doc_response}    doc_transportes
        Log    DOC ${doc_id} concluído    level=INFO
        Sleep    1s
    END
    RETURN    ${response_list}

Process Doc Transportes Entry With Browser
    [Arguments]    ${doc_entry}
    [Documentation]    Process a single doc_transportes entry in a complete browser session.
    ${doc_id}=    Get Doc Transportes Id    ${doc_entry}
    ${centro_distribuicao}=    Get Centro Distribuicao From Entry    ${doc_entry}
    ${credentials}=    Get Credentials For Centro Distribuicao    ${centro_distribuicao}
    
    ${doc_response}=    Create Dictionary    doc_transportes=${doc_id}    status=SUCCESS    error_message=${EMPTY}
    TRY
        Log    Processando DOC ${doc_id} - iniciando nova sessão do browser    level=INFO
        Execute Upload Process For Entry    ${doc_entry}    ${centro_distribuicao}    ${credentials}
        Log    Upload concluído para DOC ${doc_id}    level=INFO
    EXCEPT    AS    ${error}
        Set To Dictionary    ${doc_response}    status=FAIL    error_message=${error}
        Log    Erro ao processar DOC ${doc_id}: ${error}    level=ERROR
    END
    RETURN    ${doc_response}

Get Doc Transportes Id
    [Arguments]    ${doc_entry}
    [Documentation]    Extract doc_transportes ID from entry.
    ${doc_id}=    Get From Dictionary    ${doc_entry}    doc_transportes
    RETURN    ${doc_id}

Get Centro Distribuicao From Entry
    [Arguments]    ${doc_entry}
    [Documentation]    Extract centro_distribuicao from doc_entry, fail if not found.
    ${has_centro_distribuicao}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${doc_entry}    centro_distribuicao
    IF    not ${has_centro_distribuicao}
        ${doc_id}=    Get From Dictionary    ${doc_entry}    doc_transportes
        Fail    centro_distribuicao não encontrado no doc_entry para DOC ${doc_id}
    END
    ${centro_distribuicao}=    Get From Dictionary    ${doc_entry}    centro_distribuicao
    RETURN    ${centro_distribuicao}

Get Credentials For Centro Distribuicao
    [Arguments]    ${centro_distribuicao}
    [Documentation]    Get access credentials for centro_distribuicao from centro_access.py.
    ${access_credentials}=    Evaluate    centro_access.get_centro_distribuicao_access("${centro_distribuicao}")    modules=centro_access
    IF    ${access_credentials} == ${None}
        Fail    Credenciais não encontradas para centro_distribuicao: ${centro_distribuicao}
    END
    RETURN    ${access_credentials}

Execute Upload Process For Entry
    [Arguments]    ${doc_entry}    ${centro_distribuicao}    ${credentials}
    [Documentation]    Execute the complete upload process: browser, login, navigate, search, upload. Browser closes only after upload confirmation.
    ${usuario}=    Get From Dictionary    ${credentials}    usuario
    ${senha}=    Get From Dictionary    ${credentials}    senha
    ${doc_transportes}=    Get From Dictionary    ${doc_entry}    doc_transportes
    Log    Usando credenciais para centro_distribuicao ${centro_distribuicao}: usuario=${usuario}    level=INFO
    Log    Processando doc_transportes: ${doc_transportes}    level=INFO
    
    ${emissor_search}=    Build Emissor Search String    ${centro_distribuicao}
    
    Start Browser Session
    Login And Navigate To Upload    ${usuario}    ${senha}
    # Search and upload - this will wait for upload confirmation before returning
    Search Emissor And Upload    ${emissor_search}    ${doc_transportes}
    # Browser closes only after upload confirmation (handled in Search Emissor And Upload)
    Close Browser Session

Build Emissor Search String
    [Arguments]    ${centro_distribuicao}
    [Documentation]    Build emissor search string: "FPL" + centro_distribuicao.
    ${emissor_search}=    Set Variable    FPL${centro_distribuicao}
    Log    Usando emissor search: ${emissor_search} para centro_distribuicao: ${centro_distribuicao}    level=INFO
    RETURN    ${emissor_search}

Start Browser Session
    [Documentation]    Start a new browser session.
    Configure Screenshot Directory
    Start Browser

Login And Navigate To Upload
    [Arguments]    ${usuario}    ${senha}
    [Documentation]    Login to MultiCTE and navigate to Leitura De Canhotos.
    Login To MultiCTE    usuario=${usuario}    senha=${senha}
    Navigate To Leitura De Canhotos

Search Emissor And Upload
    [Arguments]    ${emissor_search}    ${doc_transportes}
    [Documentation]    Search for emissor and trigger upload with doc_transportes for file selection. Waits for upload completion before returning.
    Search And Select Emissor    ${emissor_search}
    Select Delivery Date And Trigger Upload    doc_transportes=${doc_transportes}
    # Ensure upload is confirmed before proceeding (handled in Select And Upload Files)
    IF    ${doc_transportes} != ${None}
        # Upload confirmation is already completed in Select And Upload Files via Wait For Upload To Complete
        Log    Upload confirmed for doc_transportes ${doc_transportes}, ready to close browser    level=INFO
    END

Close Browser Session
    [Documentation]    Close browser session only after upload confirmation. Upload must be confirmed before this is called.
    # Upload confirmation is guaranteed by Wait For Upload To Complete in Select And Upload Files
    # Close browser only after upload is confirmed
    Run Keyword And Ignore Error    Close All Browsers
    Run Keyword And Ignore Error    Close Browser

Finish Saga Execution
    [Arguments]    ${final_response}
    [Documentation]    Finish saga execution with final response if saga context is available.
    Log    Response object: ${final_response}    level=INFO
    ${exec_id}=    Get Variable Value    $robot_operator_saga_id    ${None}
    IF    ${exec_id} != ${None}
        ${success}=    Evaluate    saga_client.finish_execution_success(${exec_id}, {'response': ${final_response}})    modules=saga_client
        IF    ${success}
            Log    Response saved to robotOperatorSaga ${exec_id}    level=INFO
        ELSE
            Log    Failed to save response to robotOperatorSaga ${exec_id}    level=WARN
        END
    ELSE
        Log    No saga context available, skipping saga execution finish    level=INFO
    END
