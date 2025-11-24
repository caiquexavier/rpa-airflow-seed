*** Settings ***
Resource    ${CURDIR}/../resources/infra/browser_keywords.robot
Resource    ${CURDIR}/../resources/domain/protocolo_devolucao_keywords.robot
Resource    ${CURDIR}/../resources/saga/saga_context_keywords.robot
Library           ${CURDIR}/../libs/saga_client.py
Library           JSONLibrary

Suite Setup    Initialize Test Suite

*** Test Cases ***
Pod Download
    [Documentation]    Execute pod download.
    
    Start Browser
    Login To e-Cargo
    ${saga_data}=    Get Variable Value    $data    ${None}
    IF    ${saga_data} == ${None}
        Fail    Variável $data não encontrada no payload do listener
    END
    Load JSON Data    ${saga_data}
    ${doc_transportes_list}=    Get Saga Doc Transportes List
    Should Not Be Empty    ${doc_transportes_list}    data.doc_transportes_list não encontrado ou vazio no payload do SAGA
    ${response_list}=    Create List
    Open Operacional Menu
    FOR    ${doc_entry}    IN    @{doc_transportes_list}
        ${doc_id}=    Get From Dictionary    ${doc_entry}    doc_transportes
        ${nf_list}=    Get From Dictionary    ${doc_entry}    nf_e
        ${nf_count}=    Get Length    ${nf_list}
        IF    ${nf_count} == 0
            Fail    Nenhuma NF encontrada para doc_transportes ${doc_id}
        END
        ${nf_e_results}=    Create List
        FOR    ${nota_fiscal}    IN    @{nf_list}
            Log    DOC ${doc_id} - processando NF ${nota_fiscal}    level=INFO
            ${nf_result}=    Create Dictionary    nf=${nota_fiscal}    status=SUCCESS    error_message=${EMPTY}
            TRY
                Open Registro De Canhotos Submenu
                Input Nota Fiscal    ${nota_fiscal}
                Validate Nota Fiscal Search    ${nota_fiscal}
                ${modal_result}=    Open Nota Fiscal Modal
                ${modal_status}=    Get From Dictionary    ${modal_result}    status
                IF    '${modal_status}' == 'FAIL'
                    ${error_msg}=    Get From Dictionary    ${modal_result}    error_message
                    Set To Dictionary    ${nf_result}    status=FAIL    error_message=${error_msg}
                    Log    Business error para DOC ${doc_id} NF ${nota_fiscal}: ${error_msg}    level=WARN
                ELSE
                    Download Nota Fiscal Pdfs
                    Close Nota Fiscal Modal
                END
            EXCEPT    AS    ${error}
                Set To Dictionary    ${nf_result}    status=FAIL    error_message=${error}
                Log    Erro ao processar DOC ${doc_id} NF ${nota_fiscal}: ${error}    level=ERROR
            END
            Append To List    ${nf_e_results}    ${nf_result}
        END
        ${doc_response}=    Create Dictionary    doc_transportes=${doc_id}    nf_e=${nf_e_results}
        Append To List    ${response_list}    ${doc_response}
        Sleep    1s
        Log    DOC ${doc_id} concluído    level=INFO
    END
    ${final_response}=    Create Dictionary    doc_transportes_list=${response_list}
    Log    Response object: ${final_response}    level=INFO
    ${exec_id}=    Get Variable Value    $robot_operator_saga_id    ${None}
    IF    ${exec_id} is not ${None}
        ${success}=    Evaluate    saga_client.finish_execution_success(${exec_id}, {'response': ${final_response}})    modules=saga_client
        IF    ${success}
            Log    Response saved to robotOperatorSaga ${exec_id}    level=INFO
        ELSE
            Log    Failed to save response to robotOperatorSaga ${exec_id}    level=WARN
        END
    END
    Close Browser

*** Keywords ***
Initialize Test Suite
    [Documentation]    Initialize test suite: disable screenshots.
    Set Screenshot Directory    ${None}

##pesquisa deve ser feita pelo numero OS nao NF

