*** Settings ***
Library           Collections

*** Keywords ***
Initialize Saga Context From Arguments
    [Documentation]    Initialize saga context from variables passed by listener/Airflow.
    ...                The listener passes the entire RabbitMQ message as a JSON variable file,
    ...                which creates variables like robot_operator_saga_id, robot_operator_id, saga_id, data.
    ...                This keyword extracts and logs the saga context for debugging.
    Log    Initializing saga context from arguments    level=INFO
    
    # Check for robot_operator_saga_id (from listener message)
    ${exec_id}=    Get Variable Value    $robot_operator_saga_id    ${None}
    IF    ${exec_id} != ${None}
        Log    robot_operator_saga_id=${exec_id}    level=INFO
    ELSE
        Log    robot_operator_saga_id not provided    level=WARN
    END
    
    # Check for robot_operator_id (from listener message)
    ${rpa_key_id}=    Get Variable Value    $robot_operator_id    ${None}
    IF    ${rpa_key_id} != ${None}
        Log    robot_operator_id=${rpa_key_id}    level=INFO
    ELSE
        Log    robot_operator_id not provided    level=WARN
    END
    
    # Check for saga_id (from listener message)
    ${saga_id_value}=    Get Variable Value    $saga_id    ${None}
    IF    ${saga_id_value} != ${None}
        Log    saga_id=${saga_id_value}    level=INFO
    ELSE
        Log    saga_id not provided    level=WARN
    END
    
    # Check for data (from listener message)
    ${data_value}=    Get Variable Value    $data    ${None}
    IF    ${data_value} != ${None}
        TRY
            ${data_keys}=    Get Dictionary Keys    ${data_value}
            Log    data variable found with keys: ${data_keys}    level=INFO
        EXCEPT    AS    ${error}
            Log    data variable found but is not a dictionary: ${error}    level=WARN
        END
    ELSE
        Log    data variable not provided    level=WARN
    END

Get Saga Exec Id
    [Documentation]    Get execution ID (robot_operator_saga_id) from saga context.
    ...                This is the ID used to update saga steps via the API.
    ${exec_id}=    Get Variable Value    $robot_operator_saga_id    ${None}
    RETURN    ${exec_id}

Get Saga Rpa Key Id
    [Documentation]    Get RPA key ID (robot_operator_id) from saga context.
    ...                This identifies which robot/process is being executed.
    ${rpa_key_id}=    Get Variable Value    $robot_operator_id    ${None}
    RETURN    ${rpa_key_id}

Get Saga Step Id
    [Documentation]    Get step ID from saga context.
    ...                STEP_ID is typically generated dynamically during execution,
    ...                but may be provided in the message for specific step tracking.
    ${step_id}=    Get Variable Value    $STEP_ID    ${None}
    RETURN    ${step_id}

Get Saga Id
    [Documentation]    Get parent saga ID from saga context.
    ...                This is the ID of the parent saga that orchestrated this robot execution.
    ${saga_id_value}=    Get Variable Value    $saga_id    ${None}
    RETURN    ${saga_id_value}

