*** Variables ***
# Default saga context variables
# These should be provided via robot -v EXEC_ID:value -v RPA_KEY_ID:value etc.
# or via variable files passed by the listener/Airflow
${EXEC_ID}    ${None}
${RPA_KEY_ID}    ${None}
${STEP_ID}    ${None}
# Default doc_transportes_list matching DEFAULT_DOC_TRANSPORTES_LIST from gpt_pdf_extractor_operator.py
# Each entry includes centro_distribuicao value extracted from CD column in Excel file
${data}    {"doc_transportes_list": [{"doc_transportes": "96722724", "centro_distribuicao": "3031", "nf_e": ["4921184", "4921183", "4921190", "4921192", "4920188", "4941272", "4941187", "4941186", "4941177"]}, {"doc_transportes": "96802793", "centro_distribuicao": "3202", "nf_e": ["1301229", "1301232", "1301236", "1303468", "1301233", "1301231", "1301230", "1301234", "1301235", "1301228"]}, {"doc_transportes": "97542262", "centro_distribuicao": "3202", "nf_e": ["1319786", "1320038", "1329928", "1328276", "1328274", "1328260"]}]}

