*** Variables ***
# Default saga context variables
# These should be provided via robot -v EXEC_ID:value -v RPA_KEY_ID:value etc.
# or via variable files passed by the listener/Airflow
${EXEC_ID}    ${None}
${RPA_KEY_ID}    ${None}
${STEP_ID}    ${None}
${data}    {"doc_transportes_list": []}

