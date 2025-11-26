"""Robot Framework variable file for XPath locators used in protocolo_devolucao."""

# Navigation
XPATH_OPERACIONAL_MENU = "//*[@id='app']/div[6]/div[1]/aside/div[1]/div[2]/div[5]/div[1]"
XPATH_REGISTRO_CANHOTOS = "//div[@class='v-list__tile__title' and text()='Registro de Canhotos']"

# Search and modals
XPATH_SEARCH_BUTTON = "/html/body/div/div/div[3]/form/div[1]/div[6]/div/div[1]/button"
XPATH_ERROR_MODAL = "//*[@id='modalMensagem']/div/div/div"
XPATH_ERROR_MSG = "//*[@id='modalMensagem']/div/div/div/div[1]"
XPATH_ERROR_CLOSE = "//*[@id='modalMensagem']/div/div/div/div[2]/button"

# Nota fiscal modal
XPATH_CANHOTO_BUTTON = (
    "/html/body/div/div/div[3]/form/div[2]/div[2]/table/tbody/tr[2]/td/div/div[2]/div[3]/button"
)
XPATH_MODAL_CANHOTO = "//*[@id='ModalCanhotoNf']"


