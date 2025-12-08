*** Settings ***
Resource    ${CURDIR}/../resources/infra/browser_keywords.robot
Resource    ${CURDIR}/../resources/domain/multicte_keywords.robot
Resource    ${CURDIR}/../resources/saga/saga_context_keywords.robot
Library           ${CURDIR}/../libs/saga_client.py
Library           JSONLibrary
Library           Collections

Suite Setup    Initialize Test Suite

*** Variables ***
# Default fallback doc_transportes_list when saga is not present
# This matches DEFAULT_DOC_TRANSPORTES_LIST from gpt_pdf_extractor_operator.py

*** Test Cases ***
Upload Multi CTE For Emissor
    [Documentation]    Upload Multi CTE files for each emissor in doc_transportes_list.
    ...                Uses saga data if available, otherwise falls back to DEFAULT_DOC_TRANSPORTES_LIST.
    Start Browser
    Login To MultiCTE
    ${doc_transportes_list}=    Get Doc Transportes List With Fallback
    Should Not Be Empty    ${doc_transportes_list}    doc_transportes_list não encontrado e nenhum valor padrão disponível
    ${response_list}=    Process Doc Transportes List    ${doc_transportes_list}
    ${final_response}=    Create Dictionary    doc_transportes_list=${response_list}
    Finish Saga Execution    ${final_response}
    Close Browser

*** Keywords ***
Initialize Test Suite
    [Documentation]    Initialize test suite: disable screenshots.
    Set Screenshot Directory    ${None}

Get Doc Transportes List With Fallback
    [Documentation]    Get doc_transportes_list from saga data, or use default fallback if saga is not present.
    ${saga_data}=    Get Variable Value    $data    ${None}
    ${doc_transportes_list}=    Set Variable    ${None}
    
    IF    ${saga_data} != ${None}
        TRY
            ${parsed}=    Convert Saga Payload To Dict    ${saga_data}
            ${has_doc_list}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${parsed}    doc_transportes_list
            IF    ${has_doc_list}
                ${doc_transportes_list}=    Get From Dictionary    ${parsed}    doc_transportes_list
            ELSE
                ${has_data_node}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${parsed}    data
                IF    ${has_data_node}
                    ${data_node}=    Get From Dictionary    ${parsed}    data
                    ${has_doc_list_in_data}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${data_node}    doc_transportes_list
                    IF    ${has_doc_list_in_data}
                        ${doc_transportes_list}=    Get From Dictionary    ${data_node}    doc_transportes_list
                    END
                END
            END
            Log    Using doc_transportes_list from saga data    level=INFO
        EXCEPT    AS    ${error}
            Log    Failed to parse saga data: ${error}. Using default fallback.    level=WARN
        END
    END
    
    ${is_none}=    Evaluate    $doc_transportes_list is None
    IF    ${is_none}
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

Create Default Doc Transportes List
    [Documentation]    Create default doc_transportes_list matching DEFAULT_DOC_TRANSPORTES_LIST from gpt_pdf_extractor_operator.py.
    ${default_json}=    Set Variable    [{"doc_transportes": "96722724", "centro": "3202", "nf_e": ["4921184", "4921183", "4921190", "4921192", "4920188", "4941272", "4941187", "4941186", "4941177"]}, {"doc_transportes": "96802793", "centro": "5183", "nf_e": ["1301229", "1301232", "1301236", "1303468", "1301233", "1301231", "1301230", "1301234", "1301235", "1301228"]}, {"doc_transportes": "97542262", "centro": "3031", "nf_e": ["1319786", "1320038", "1329928", "1328276", "1328274", "1328260"]}]
    ${default_list}=    Convert String To Json    ${default_json}
    RETURN    ${default_list}

Convert Saga Payload To Dict
    [Arguments]    ${payload}
    ${is_string}=    Evaluate    isinstance(${payload}, str)
    IF    ${is_string}
        ${result}=    Convert String To Json    ${payload}
    ELSE
        ${result}=    Set Variable    ${payload}
    END
    RETURN    ${result}

Process Doc Transportes List
    [Arguments]    ${doc_transportes_list}
    [Documentation]    Process each doc_transportes entry in the list.
    ${response_list}=    Create List
    Navigate To Leitura De Canhotos
    FOR    ${doc_entry}    IN    @{doc_transportes_list}
        ${doc_response}=    Process Single Doc Transportes    ${doc_entry}
        Append To List    ${response_list}    ${doc_response}
        ${doc_id}=    Get From Dictionary    ${doc_response}    doc_transportes
        Log    DOC ${doc_id} concluído    level=INFO
        Sleep    1s
    END
    RETURN    ${response_list}

Process Single Doc Transportes
    [Arguments]    ${doc_entry}
    [Documentation]    Process a single doc_transportes entry: search and select emissor, then trigger upload.
    ${doc_id}=    Get From Dictionary    ${doc_entry}    doc_transportes
    ${doc_response}=    Create Dictionary    doc_transportes=${doc_id}    status=SUCCESS    error_message=${EMPTY}
    TRY
        Log    Processando DOC ${doc_id}    level=INFO
        Search And Select Emissor    ${doc_id}
        Select Delivery Date And Trigger Upload
        Log    Upload concluído para DOC ${doc_id}    level=INFO
    EXCEPT    AS    ${error}
        Set To Dictionary    ${doc_response}    status=FAIL    error_message=${error}
        Log    Erro ao processar DOC ${doc_id}: ${error}    level=ERROR
    END
    RETURN    ${doc_response}

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

