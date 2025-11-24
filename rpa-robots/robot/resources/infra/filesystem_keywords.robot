*** Settings ***
Library           OperatingSystem
Library           Collections

*** Keywords ***
Ensure Directory Exists
    [Arguments]    ${directory_path}
    [Documentation]    Create directory if it does not exist.
    ${exists}=    Run Keyword And Return Status    Directory Should Exist    ${directory_path}
    IF    not ${exists}
        Create Directory    ${directory_path}
    END

Get File Name From Path
    [Arguments]    ${file_path}
    [Documentation]    Extract filename from file path.
    ${filename}=    Evaluate    os.path.basename(r"${file_path}")    os
    RETURN    ${filename}

Move File To Directory
    [Arguments]    ${source_file}    ${target_dir}
    [Documentation]    Move file to target directory, creating directory if needed.
    Ensure Directory Exists    ${target_dir}
    ${filename}=    Get File Name From Path    ${source_file}
    ${target_file}=    Evaluate    os.path.join(r"${target_dir}", r"${filename}")    os
    ${source_exists}=    Run Keyword And Return Status    File Should Exist    ${source_file}
    IF    not ${source_exists}
        Fail    Source file does not exist: ${source_file}
    END
    ${moved}=    Run Keyword And Return Status    Move File    ${source_file}    ${target_file}
    IF    ${moved}
        ${verify_moved}=    Run Keyword And Return Status    File Should Exist    ${target_file}
        IF    not ${verify_moved}
            Fail    File move reported success but target file not found: ${target_file}
        END
    ELSE
        Copy File    ${source_file}    ${target_file}
        ${copied_exists}=    Run Keyword And Return Status    File Should Exist    ${target_file}
        IF    ${copied_exists}
            Remove File    ${source_file}
        ELSE
            Fail    Failed to copy file to ${target_dir}
        END
    END

