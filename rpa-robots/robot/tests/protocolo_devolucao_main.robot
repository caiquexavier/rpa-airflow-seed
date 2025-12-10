*** Settings ***
Resource    ${CURDIR}/../resources/infra/browser_keywords.robot
Resource    ${CURDIR}/../resources/domain/protocolo_devolucao_keywords.robot
Resource    ${CURDIR}/../resources/saga/saga_context_keywords.robot
Library           ${CURDIR}/../libs/saga_client.py
Library           JSONLibrary

Suite Setup    Initialize Test Suite
Suite Teardown    Cleanup Screenshots

*** Test Cases ***
Pod Download
    [Documentation]    Execute pod download.
    
    Start Browser
    Login To e-Cargo
    ${saga_data}=    Get Saga Payload
    Load JSON Data    ${saga_data}
    ${doc_transportes_list}=    Get Saga Doc Transportes List
    Should Not Be Empty    ${doc_transportes_list}    data.doc_transportes_list não encontrado ou vazio no payload do SAGA
    ${response_list}=    Process Doc Transportes List    ${doc_transportes_list}
    ${final_response}=    Create Dictionary    doc_transportes_list=${response_list}
    Finish Saga Execution    ${final_response}
    Close Browser

*** Keywords ***
Initialize Test Suite
    [Documentation]    Initialize test suite: configure screenshots to save in results folder.
    Configure Screenshot Directory

Get Saga Payload
    ${saga_data}=    Get Variable Value    $data    ${None}
    IF    ${saga_data} == ${None}
        Fail    Variável $data não encontrada no payload do listener
    END
    RETURN    ${saga_data}

Process Doc Transportes List
    [Arguments]    ${doc_transportes_list}
    ${response_list}=    Create List
    Open Operacional Menu
    ${is_first_doc}=    Set Variable    ${True}
    FOR    ${doc_entry}    IN    @{doc_transportes_list}
        ${doc_response}=    Process Single Doc Transportes    ${doc_entry}    ${is_first_doc}
        Append To List    ${response_list}    ${doc_response}
        Sleep    1s
        ${doc_id}=    Get From Dictionary    ${doc_response}    doc_transportes
        Log    DOC ${doc_id} concluído    level=INFO
        ${is_first_doc}=    Set Variable    ${False}
    END
    RETURN    ${response_list}

Process Single Doc Transportes
    [Arguments]    ${doc_entry}    ${is_first_doc}=${True}
    ${doc_id}=    Get From Dictionary    ${doc_entry}    doc_transportes
    ${nf_list}=    Get From Dictionary    ${doc_entry}    nf_e
    ${nf_count}=    Get Length    ${nf_list}
    IF    ${nf_count} == 0
        Fail    Nenhuma NF encontrada para doc_transportes ${doc_id}
    END
    # Process only the first NF-e value for each doc_transportes
    ${nota_fiscal}=    Get From List    ${nf_list}    0
    ${nf_result}=    Process Nota Fiscal    ${doc_id}    ${nota_fiscal}    ${is_first_doc}
    ${nf_e_results}=    Create List    ${nf_result}
    ${doc_response}=    Create Dictionary    doc_transportes=${doc_id}    nf_e=${nf_e_results}
    RETURN    ${doc_response}

Process Nota Fiscal
    [Arguments]    ${doc_id}    ${nota_fiscal}    ${is_first_nf}=${True}
    Log    DOC ${doc_id} - processando NF ${nota_fiscal}    level=INFO
    ${nf_result}=    Create Dictionary    nf=${nota_fiscal}    status=SUCCESS    error_message=${EMPTY}
    TRY
        IF    ${is_first_nf}
            Open Registro De Canhotos Submenu
        END
        Input Nota Fiscal    ${nota_fiscal}
        Validate Nota Fiscal Search    ${nota_fiscal}
        ${modal_result}=    Open Nota Fiscal Modal
        ${modal_status}=    Get From Dictionary    ${modal_result}    status
        IF    '${modal_status}' == 'FAIL'
            ${error_msg}=    Get From Dictionary    ${modal_result}    error_message
            Set To Dictionary    ${nf_result}    status=FAIL    error_message=${error_msg}
            Log    Business error para DOC ${doc_id} NF ${nota_fiscal}: ${error_msg}    level=WARN
            # Click Voltar after error to return to search page
            Click Voltar Button
        ELSE
            Download Nota Fiscal Pdfs    ${nota_fiscal}
            Close Nota Fiscal Modal
            # Click Voltar after closing modal to return to search page for next doc_transportes
            Click Voltar Button
        END
    EXCEPT    AS    ${error}
        Set To Dictionary    ${nf_result}    status=FAIL    error_message=${error}
        Log    Erro ao processar DOC ${doc_id} NF ${nota_fiscal}: ${error}    level=ERROR
    END
    RETURN    ${nf_result}

Finish Saga Execution
    [Arguments]    ${final_response}
    Log    Response object: ${final_response}    level=INFO
    ${exec_id}=    Get Variable Value    $robot_operator_saga_id    ${None}
    IF    ${exec_id} != ${None}
        ${success}=    Evaluate    saga_client.finish_execution_success(${exec_id}, {'response': ${final_response}})    modules=saga_client
        IF    ${success}
            Log    Response saved to robotOperatorSaga ${exec_id}    level=INFO
        ELSE
            Log    Failed to save response to robotOperatorSaga ${exec_id}    level=WARN
        END
    END
