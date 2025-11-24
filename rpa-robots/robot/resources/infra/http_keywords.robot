*** Settings ***
Library           ${CURDIR}/../../libs/rpa_api_client.py

*** Keywords ***
Call RPA API
    [Arguments]    ${endpoint}    ${method}=GET    ${payload}=${None}    ${timeout}=30
    [Documentation]    Make a generic API call to rpa-api.
    ...                This keyword wraps the Python library call_api function.
    ...
    ...                Args:
    ...                - endpoint: API endpoint (e.g., "/api/v1/saga/123")
    ...                - method: HTTP method (GET, POST, PUT, DELETE), default: GET
    ...                - payload: Optional request payload (dict), default: None
    ...                - timeout: Request timeout in seconds, default: 30
    ...
    ...                Returns:
    ...                Response JSON as dict if successful, None otherwise
    ${response}=    Call Api    ${endpoint}    method=${method}    payload=${payload}    timeout=${timeout}
    RETURN    ${response}
