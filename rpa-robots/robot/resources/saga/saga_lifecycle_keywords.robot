*** Settings ***
Library           ${CURDIR}/../../libs/saga_client.py
Resource          ${CURDIR}/saga_context_keywords.robot

*** Keywords ***
Saga Start Step
    [Arguments]    ${step_name}    ${step_data}=${None}
    [Documentation]    Start a saga step. Calls Python library to update saga via API.
    ${exec_id}=    Get Saga Exec Id
    ${rpa_key_id}=    Get Saga Rpa Key Id
    ${step_id}=    Get Saga Step Id
    
    IF    ${exec_id} is None
        Log    Cannot start step: EXEC_ID not available    level=WARN
        RETURN
    END
    
    TRY
        Start Step    ${exec_id}    ${step_name}    ${step_id}    ${step_data}
        Log    Started saga step: ${step_name}    level=INFO
    EXCEPT    AS    ${error}
        Log    Failed to start saga step: ${error}    level=ERROR
    END

Saga Mark Step Success
    [Arguments]    ${step_name}    ${step_data}=${None}
    [Documentation]    Mark a saga step as successful. Calls Python library to update saga via API.
    ${exec_id}=    Get Saga Exec Id
    ${step_id}=    Get Saga Step Id
    
    IF    ${exec_id} is None
        Log    Cannot mark step success: EXEC_ID not available    level=WARN
        RETURN
    END
    
    TRY
        Mark Step Success    ${exec_id}    ${step_name}    ${step_id}    ${step_data}
        Log    Marked saga step as success: ${step_name}    level=INFO
    EXCEPT    AS    ${error}
        Log    Failed to mark saga step success: ${error}    level=ERROR
    END

Saga Mark Step Fail With Message
    [Arguments]    ${step_name}    ${error_message}    ${step_data}=${None}
    [Documentation]    Mark a saga step as failed with error message. Calls Python library to update saga via API.
    ${exec_id}=    Get Saga Exec Id
    ${step_id}=    Get Saga Step Id
    
    IF    ${exec_id} is None
        Log    Cannot mark step fail: EXEC_ID not available    level=WARN
        RETURN
    END
    
    TRY
        Mark Step Fail    ${exec_id}    ${step_name}    ${step_id}    ${error_message}    ${step_data}
        Log    Marked saga step as failed: ${step_name} - ${error_message}    level=ERROR
    EXCEPT    AS    ${error}
        Log    Failed to mark saga step fail: ${error}    level=ERROR
    END

Saga Finish Execution Success
    [Arguments]    ${execution_data}=${None}
    [Documentation]    Finish execution as successful. Calls Python library to update saga via API.
    ${exec_id}=    Get Saga Exec Id
    
    IF    ${exec_id} is None
        Log    Cannot finish execution: EXEC_ID not available    level=WARN
        RETURN
    END
    
    TRY
        Finish Execution Success    ${exec_id}    ${execution_data}
        Log    Finished execution as success    level=INFO
    EXCEPT    AS    ${error}
        Log    Failed to finish execution: ${error}    level=ERROR
    END

Saga Finish Execution Fail
    [Arguments]    ${error_message}    ${execution_data}=${None}
    [Documentation]    Finish execution as failed with error message. Calls Python library to update saga via API.
    ${exec_id}=    Get Saga Exec Id
    
    IF    ${exec_id} is None
        Log    Cannot finish execution: EXEC_ID not available    level=WARN
        RETURN
    END
    
    TRY
        Finish Execution Fail    ${exec_id}    ${error_message}    ${execution_data}
        Log    Finished execution as failed: ${error_message}    level=ERROR
    EXCEPT    AS    ${error}
        Log    Failed to finish execution: ${error}    level=ERROR
    END

