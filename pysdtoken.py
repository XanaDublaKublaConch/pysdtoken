"""
Provide python access to th eRSA Soft Token Service
This module wraps the stauto32.dll calls using
ctypes to get the current code from the token
"""
import platform
from ctypes import *
from enum import Enum
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())

# A struct to hold token error information
class struct_tagTOKENERRORINFO(Structure):
    _pack_ = 1  # source:False
    _fields_ = [
        ('error', c_int32),
        ('error_string', c_char * 24),
        ('detailed_error_string', c_char * 64),
    ]


token_error_info = struct_tagTOKENERRORINFO


# A struct to hold token information
class struct_tagTOKENBASICINFO(Structure):
    _pack_ = 1  # source:False
    _fields_ = [
        ('dwSize', c_long),
        ('serialnumber', c_char * 24),
        ('username', c_char * 24),
        ('deviceID', c_char * 24),
        ('descriptor', c_char * 64),
    ]


token_basic_info = struct_tagTOKENBASICINFO

# Enum for Errors
class TokenError(Enum):
    ERROR_DISPLAY_STRING = -1
    ERROR_INIT = 1
    ERROR_INVALID_PNTR = 1
    ERROR_TIME = 2
    ERROR_DLL_LOADED = 2
    ERROR_SOFTID_CANNOTRUN = 2
    ERROR_LOAD_DLL_ERROR = 3
    ERROR_SECURITY = 3
    ERROR_SOFTID_DEAD = 3
    ERROR_RESOURCE_ERROR = 4
    ERROR_READ_REG_ERROR = 5
    ERROR_WRITE_REG_ERROR = 6
    ERROR_INVALID_SET=NUMBER = 7
    ERROR_PROC_ADDRESS_ERROR = 8
    ERROR_INVALID_NAME_ERROR = 9
    ERROR_DLL_CALL_ERROR = 10
    ERROR_INACTIVE_DLL = 11
    ERROR_DATA_INVALID = 12
    ERROR_HANDLE_INVALID = 13
    ERROR_KEY_INVALID = 14
    ERROR_TOKEN_INVALID = 15
    ERROR_TOKEN_NOTFOUND = 16
    ERROR_BUFFER_TOO_SMALL_ERROR = 17
    ERROR_TOKEN_SERVICE_OPEN = 18
    ERROR_INVALID_COMP_NAME = 19
    ERROR_SET_ONE_DELETED = 20
    ERROR_PASSWORD_INVALID = 21
    ERROR_NONE_MATCHING_PASSWORD = 22
    ERROR_COPY_PROTECTION_DEVICE = 23
    ERROR_COPY_PROTECTION_TOKEN = 24
    ERROR_TOKENCODE_GENERATION = 25
    ERROR_DATABASE = 26
    ERROR_LOAD_LIBRARY = 27
    ERROR_OPEN_FILE = 28
    ERROR_OPEN_DATABASE = 29
    ERROR_SCARD = 30
    ERROR_P_ELEVEN = 31
    ERROR_PLUGIN = 32
    ERROR_SDD = 33
    ERROR_PSD = 34
    ERROR_DEVICE_LOGIN = 35
    ERROR_SELECT_TOKEN_SERIAL = 36
    ERROR_DEVICE_BINDING = 37
    ERROR_GUID_INVALID = 38
    ERROR_PLUGIN_IMPLEMENTATION = 39
    ERROR_FILE_FORMAT = 40
    ERROR_INET_COMMUNICATION = 41
    ERROR_TOKENFILE_PASSWORD_CHECK = 42
    ERROR_SERVER_BAD_STATUS = 43
    ERROR_DUPLICATE_SERIAL = 44
    ERROR_SSL_UNTRUSTED_CERT = 45
    ERROR_DEVICE_FULL = 46
    ERROR_DEVICE_RESET = 47
    ERROR_EXPIRED_TOKEN = 48
    ERROR_PASSWORD_FAILURE = 216
    ERROR_IMPORT_FAILURE = 217
    ERROR_MAX_IMPORT_TOKENS = 49


# A struct to hold dates
class struct_CK_DATE(Structure):
    _pack = True  # source:False
    _fields = [
        ('year', c_ubyte * 4),
        ('month', c_ubyte * 2),
        ('day', c_ubyte * 2),
    ]


CKDATE = struct_CK_DATE


class Token:
    """
    Token object to hold token info and function calls
    """

    def __init__(self, token_data):
        # Take a dict and parse it out
        self.serialnumber = token_data['serialnumber']
        self.username = token_data['username']
        self.deviceID = token_data['deviceID']
        self.descriptor = token_data['descriptor']
        self.is_default = token_data['is_default']

    def get_expiration_date(self, token_service):
        return token_service.get_token_expiration_date(self.serialnumber)

    def get_current_code(self, token_service, pin=''):
        return token_service.get_token_current_code(self.serialnumber, pin)


class SDProcess:

    tokens = []
    lTokens = c_long()

    def __init__(self, dll_name='', log_level=''):
        # Get the SD process

        if log_level.casefold() == 'NOTSET'.casefold():
            n_log_level = logging.NOTSET
        elif log_level.casefold() == 'CRITICAL'.casefold():
            n_log_level = logging.CRITICAL
        elif log_level.casefold() == 'ERROR'.casefold():
            n_log_level = logging.ERROR
        elif log_level.casefold() == 'Warning'.casefold():
            n_log_level = logging.WARNING
        elif log_level.casefold() == 'INFO'.casefold():
            n_log_level = logging.INFO
        elif log_level.casefold() == 'DEBUG'.casefold():
            n_log_level = logging.DEBUG
        else:
            n_log_level = logging.WARNING
            logger.warning('Log level: {} is not a supported option. Set to warning.'.format(log_level))

        if log_level != '':
            logger.setLevel(n_log_level)

        self.dll_name = dll_name

        if platform.system() == 'Windows':
            try:
                if self.dll_name == '':
                    self.dll_name = 'stauto32.dll'  # Is there a default location on windows?
                self.process = windll.LoadLibrary(self.dll_name)
            except Exception as e:
                logger.debug(e)
                logger.error("Error finding Soft Token service.")
        else:
            try:
                if self.dll_name == '':
                    self.dll_name = '/Library/Frameworks/stauto32.framework/Versions/Current/stauto32'
                self.process = cdll.LoadLibrary(self.dll_name)
            except Exception as e:
                logger.debug(e)
                logger.error("Error finding Soft Token service.")

        self.handle = c_long()
        self.lDefaultToken = c_long()
        self.open_service()
        # Populate lTokens and dwBuffersize
        self.dwBuffersize = self.count_tokens()
        logger.debug("DEBUG: There are {} tokens.".format(self.lTokens.value))
        # Populate the token dict
        self.tokens = self.get_tokens()
        for stoken in self.tokens:
            logger.debug("{0}: {1}".format(stoken.serialnumber, "Default" if stoken.is_default else ""))

    def open_service(self):
        try:
            # > 0 means success and dwBuffersize is set
            if self.process.OpenTokenService(byref(self.handle)) > 0:
                logger.debug("DEBUG: Token service started, handle {}.".format(self.handle.value))
            else:
                logger.error("No token service found!")
        except Exception as e:
            logger.debug(e)
            logger.error("Error opening token service.")

    def close_service(self):
        try:
            # > 0 means success
            if self.process.CloseTokenService(self.handle.value) > 0:
                logger.debug("DEBUG: Token Service closed")
            else:
                logger.debug("Could not close token service.")
                self.get_token_error()
        except Exception as e:
            logger.debug(e)
            logger.error("Error closing service.")

    def count_tokens(self):
        # See if there are any registered tokens and set up the buffer
        dwBuffersize = c_long()
        try:
            # lTokens gets filled with the token count. Don't provide a token array pointer yet
            # Send 0 the first time in case there are no tokens to grab
            self.process.EnumToken(self.handle, byref(self.lTokens), byref(self.lDefaultToken), 0, byref(dwBuffersize))
        except Exception as e:
            logger.debug(e)
            logger.error("Error getting number of tokens.")
            return ''

        # if we got here, we didn't receive an error from the token service. The token count
        # is now stored in lTokens as a LONG
        if self.lTokens.value > 0:
            return dwBuffersize
        else:
            self.get_token_error()
            return c_long(0)

    def get_tokens(self):
        # Get the number of tokens registered with the token service by enumerating. The lTokens
        # var gets filled with a count. lDefaultToken gets filled with the index of the system
        # default token in the returned array

        # First, see if there are any registered tokens. If not, return an empty dict
        if self.lTokens.value == 0:
            logger.debug("There are no registered tokens.")
            return {}

        # Create an array of token structs
        lpTokens = (token_basic_info * self.lTokens.value)()
        tokens = []

        # There are lTokens # of tokens. Get them in an array. The dwBuffersize has to have been set
        # previously, which is done during init in the count_tokens() call. If dwBuffer points to a
        # null DWORD, the function will return zero/false and fill dwBuffersize with the correct size
        try:
            if self.process.EnumToken(self.handle, byref(self.lTokens), byref(self.lDefaultToken), byref(lpTokens),
                                      byref(self.dwBuffersize)) > 0:
                logger.debug("{} tokens found:".format(self.lTokens.value))
            else:
                logger.debug("Did not find any tokens.")
                self.get_token_error()

        except Exception as e:
            logger.debug(e)
            logger.error("Error getting tokens.")
            self.get_token_error()
            return []

        # Grab the token basic info for each token into a Token array. All stauto32 strings are utf-8
        for x, token in enumerate(lpTokens):
            token_data = {}
            token_data.update({'serialnumber': token.serialnumber.decode('utf-8')})
            token_data.update({'username': token.username.decode('utf-8')})
            token_data.update({'deviceID': token.deviceID})
            token_data.update({'descriptor': token.descriptor})
            if self.lDefaultToken.value == x:
                token_data.update({'is_default': True})
            else:
                token_data.update({'is_default': False})
            tokens.append(Token(token_data))
        return tokens

    def get_default_token(self):
        if self.lTokens.value > 0:
            return self.tokens[self.lDefaultToken.value]
        else:
            return None

    def get_token_current_code(self, serial, pin=''):
        # get the current code that would be displayed on the token screen
        # return a tuple of code + time-left
        chPASSCODE = c_char_p("one".encode("utf-8"))
        chPRN = c_char_p("two".encode("utf-8"))
        chPIN = c_char_p(pin.encode('utf-8'))
        lTimeLeft = c_long()
        try:
            self.process.GetCurrentCode(self.handle, serial.encode("utf-8"), chPIN,
                                        byref(lTimeLeft), chPASSCODE, chPRN)
        except Exception as e:
            logger.debug(e)
            logger.error("Error getting token code.")
            self.get_token_error()
        # On pinless tokens, PASSCODE and PRN will be the same
        return chPASSCODE.value.decode('utf-8'), chPRN.value.decode('utf-8'), lTimeLeft.value

    def get_token_expiration_date(self, serial):
        # Get the expiration date of the token with this serial number
        # The date is returned as a CKDATE struct
        eDate = CKDATE()

        # Get the struct and parse it - Should I use datetime library here instead of a string?
        try:
            # > 0 means success
            if self.process.GetTokenExpiration(self.handle, serial.encode('utf-8'), byref(eDate)) > 0:
                token_expiration = "{0}/{1}/{2}".format(bytes(eDate.month).decode('utf-8'),
                                                        bytes(eDate.day).decode('utf-8'),
                                                        bytes(eDate.year).decode('utf-8')
                                                        )
            else:
                self.get_token_error()
                token_expiration = None
        except Exception as e:
            logger.debug(e)
            logger.error("Error getting token expiration date.")
            self.get_token_error()
            token_expiration = None

        return token_expiration

    def get_token_error(self):
        # Get any token error. Create a TOKENERRORINFO struct
        token_error = token_error_info()
        # get a pointer to use in the dll call
        lp_token_error = pointer(token_error)
        # Call the dll function, pass in the struct pointer to get filled. > 0 is success
        if self.process.GetTokenError(self.handle, lp_token_error) > 0:
            if lp_token_error is not None and token_error is not None:
                # Dereference the pointer/get contents
                content = lp_token_error.contents
                if content.error != 0:
                    err_number = int(content.error)
                    logger.debug("{0}: {1}".format(err_number, TokenError(err_number).name))
                else:
                    logger.debug("No errors reported.")
            else:
                logger.debug("Returned NULL pointer.")
        else:
            logger.debug("No token error content.")
