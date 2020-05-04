"""
Provide python access to th eRSA Soft Token Service
This module wraps the stauto32.dll calls using
ctypes to get the current code from the token
"""
from __future__ import annotations
import platform
import logging
from typing import List, Dict, Union, NamedTuple, Tuple, Any, ByteString
from pathlib import Path
from collections import namedtuple
from datetime import date
from ctypes import c_long, c_int, c_char_p, c_void_p, windll, cdll, byref, create_string_buffer, pointer, POINTER, \
    c_int64
from ctypes.wintypes import DWORD, INT, LONG, LPLONG, LPVOID, LPDWORD, LPSTR, LPCSTR
from ._sdauto import ck_date, token_basic_info, token_error_info, TokenError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

if platform.system() == "Darwin":
    """ Support Mac OS """
    logger.debug("Identified Darwin system. Setting up Mac Darwin OS typedefs for wintypes names.")
    DWORD = c_long
    INT = c_int
    LONG = c_long
    LPSTR = c_char_p
    LPCSTR = POINTER(c_char_p)
    LPLONG = POINTER(LONG)
    LPDWORD = POINTER(DWORD)
    LPVOID = c_void_p


class Token:
    """
    Token object to hold token info and function calls
    :param token_data: A dictionary of token information
    """

    def __init__(self, serial, token_data: Dict):
        logger.debug('Initializing token with token data.')
        self.serial_number = serial
        self.process = token_data.get('token_service', None)
        if not self.process:
            logger.warning("New token created without SD process. No active process methods will work.")
        logger.debug(f'SDProcess object: {self.process}')
        logger.debug(f'Serial: {self.serial_number}')
        self.username = token_data.get('username', None)
        logger.debug(f'Username: {self.username}')
        self.deviceID = token_data.get('device_id', None)
        logger.debug(f'DeviceID: {self.deviceID}  (May be unused)')
        self.descriptor = token_data.get('descriptor', None)
        logger.debug(f'Descriptor: {self.descriptor}  (May be unused)')
        self.is_default = token_data.get('is_default', False)
        logger.debug(f'Default: {self.is_default}')
        # If a pin-style is not given, default to PINLess
        self.pin_style = token_data.get("pin_style", SDProcess.valid_pin_styles[0])
        logger.debug(f'Pin-Style: {self.pin_style}')

    def __repr__(self):
        # The most useful info (IMHO) is serial and pin-style. Serial is required and pin-style helps determine
        # the passcode length
        if self.is_default:
            starburns = "*"
        else:
            starburns = ""
        return f"Token({self.serial_number}, {self.pin_style}){starburns}"

    def get_expiration_date(self):
        """
        The expiration date is not provided by the initial token enumeration. This function calls the SDProcess using
        the token's serial to get the expiration date from the service.
        :return: datetime
        """
        if not self.process:
            logger.critical('No SDProcess found while getting expiration date!')
            raise ReferenceError("No SDProcess found")

        logger.info(f'Calling SDProcess to get expiration date for token {self.serial_number}')
        return self.process.get_token_expiration_date(self.serial_number)

    def get_current_code(self, pin: str = '') -> NamedTuple:
        """
        Calls the SDProcess to get the current code from the token with the given serial

        :param pin: a string representation of the 6-8 character alphanumeric pin
        :return: a named tuple of passcode, tokencode, and time left
        """
        if not self.process:
            logger.critical('No SDProcess found while getting current token code!')
            raise ReferenceError("No SDProcess found")

        TokenInfo = namedtuple('TokenInfo', 'passcode tokencode time_left')
        # use the *args syntax to break the returned tuple into 3 items
        logger.info(f'Calling SDProcess to get current code for token {self.serial_number}')
        return TokenInfo(*self.process.get_token_current_code(self.serial_number, self.pin_style, pin))

    def get_next_code(self, pin: str = '') -> NamedTuple:
        """
        Calls the SDProcess to get the next code from the token with the given serial
        :param pin: a string representation of the 6-8 character alphanumeric pin
        :return: a named tuple of passcode, tokencode, and time left
        """
        if not self.process:
            logger.critical('No SDProcess found while getting next token code!')
            raise ReferenceError("No SDProcess found")

        TokenInfo = namedtuple('TokenInfo', 'passcode tokencode time_left')
        logger.info(f'Calling SDProcess to get next code for token {self.serial_number}')
        return TokenInfo(*self.process.get_token_next_code(self.serial_number, pin))

    def set_sd_process(self, token_service: SDProcess) -> None:
        logger.info(f"Setting the SDProcess to object: {SDProcess}")
        self.process: SDProcess = token_service

    def set_pin_style(self, pinstyle: str) -> None:
        if pinstyle not in SDProcess.valid_pin_styles:
            raise ValueError(f"Invalid pin-style. {pinstyle} not in {SDProcess.valid_pin_styles}")

        self.pin_style = pinstyle


class SDProcess:
    """
    This class gets a handle to the sdauto32 soft token process to enable automation.     Initialize the SDProcess with
    some defaults and build the token list.
    :param dll_name: different OS have different sduato32 locations
    :param log_level: set the logging level for the class
    :param pin_length: pins can be 6-8 alphanumeric characters or 0 for pinless tokens
    :param tokencode_length: tokencodes can be 6-8 digits
    """
    # This is what RSA calls the pin styles
    valid_pin_styles = ("PINless", "PINPad-style", "Fob-style")

    def __init__(self, dll_name='', log_level='WARNING', pin_length=8, tokencode_length=8, pin_style="PINless"):
        # Set the logging level
        if log_level.casefold() == 'NOTSET'.casefold():
            n_log_level = logging.NOTSET
        elif log_level.casefold() == 'CRITICAL'.casefold():
            n_log_level = logging.CRITICAL
        elif log_level.casefold() == 'ERROR'.casefold():
            n_log_level = logging.ERROR
        elif log_level.casefold() == 'WARNING'.casefold():
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

        logging.debug('Initializing the SDProcess (calling sdauto32 init)')
        # Sanity check
        if pin_style not in self.valid_pin_styles:
            logger.warning(f"Invalid pin style {pin_style}. Setting to {self.valid_pin_styles[0]}")
            self.pin_style = self.valid_pin_styles[0]
        else:
            self.pin_style = pin_style
            logger.debug(f'Pin style set to {self.pin_style}')

        if dll_name:  # Passed in from init args
            self.dll_name = dll_name
            logger.debug(f'DLL name set to {self.dll_name} from arguments')

        else:
            logger.debug("No dll name passed in during initialization. Determining correct default from platform/arch")
            if platform.system() == 'Windows':
                logger.debug("This is a windows platform.")
                if platform.architecture()[0] == "64bit":
                    logger.debug("This is a 64-bit platform.")
                    dll_path = Path(r"C:\Program Files\RSA SecurID Token Common\stauto32.dll")
                    logger.info(f"Using path {dll_path}")
                else:
                    logger.debug("This is a 32-bit platform.")
                    dll_path = Path(r"C:\Program Files (x86)\RSA SecurID Token Common\stauto32.dll")
                    logger.info(f"Using path {dll_path}")
                if dll_path.exists():
                    logger.debug(f"dll path {dll_path} exists.")
                    self.dll_name = str(dll_path)
                else:
                    logger.warning(f"dll path {dll_path} does not exist. Setting dll_name to stauto32.dll")
                    self.dll_name = 'stauto32.dll' # Hopefully, it's in the path
                try:
                    logger.debug(f"Loading {dll_path} using ctypes windll method")
                    self.process = windll.LoadLibrary(self.dll_name)
                except Exception as e:
                    logger.debug(e)
                    logger.error("Error finding Soft Token service.")
                    return

            else:
                logger.debug("Non-windows system identified")
                try:
                    if self.dll_name == '':  # Don't use path locating. Call explicit default location.
                        self.dll_name = '/Library/Frameworks/stauto32.framework/Versions/Current/stauto32'
                    logger.debug(f"Loading {dll_name} using ctypes cdll method")
                    self.process = cdll.LoadLibrary(self.dll_name)
                except Exception as e:
                    logger.debug(e)
                    logger.error("Error finding Soft Token service.")
                    return

        logger.debug("Loaded {} successfully".format(self.dll_name))

        # Validate pin-length
        if pin_length in range(6, 9) or pin_length == 0:
            logger.debug(f'Pin length is valid {pin_length}')
            self.pin_length = pin_length
        else:
            logger.error(f'Invalid pin length {pin_length}')
            raise ValueError(f"Invalid pin length {pin_length}")

        # Validate tokencode length (can be 6-8 digits)
        if tokencode_length in range(6,9):
            logger.debug(f'Tokencode is set to {tokencode_length} digits')
            self.tokencode_length = tokencode_length
        else:
            logger.error(f'Invalid tokencode length provided')
            raise ValueError(f"Bad value for tokencode length {tokencode_length}")

        logger.info("Setting up SDProcess vars.")
        self.tokens = []
        self.lTokens = LONG()
        self.lTokenServiceHandle = LONG()
        self.lDefaultToken = LONG()
        self.lTimeLeft = LONG()
        self.dwBuffersize = DWORD(0)

        # Open the service
        logger.info(f"Opening SD Process from init")
        self.open_service()

        # Populate lTokens and dwBuffersize
        logger.info(f"Enumerating tokens from init")
        self.enum_tokens()
        logger.debug(f"There are {self.lTokens.value} tokens.")

        # Populate the token dict
        logger.info("Populating token dictionary from init")
        self.tokens = self.get_tokens()

    def open_service(self):
        """
        Python wrapper for the C++ call using ctypes this method should return a handle to the process that manages
        tokens using the sdauto32.dll typelib
        """
        svc_open = self.process.OpenTokenService
        if platform.architecture()[0] == "64bit":
            logger.debug("Setting return type of OpenTokenService to c_int64")
            svc_open.restype = c_int64
        else:
            svc_open.restype = c_int

        logger.debug(f'Setting args for OpenTokenService to POINTER(c_long)')
        svc_open.argtypes = [POINTER(c_long),]

        try:
            # > 0 means success and dwBuffersize is set
            logger.debug("Calling OpenTokenService function with ctypes")
            if svc_open(self.lTokenServiceHandle) > 0:
                logger.debug(f"Token service started, handle {self.lTokenServiceHandle.value}.")
            else:
                logger.error("No token service found!")
        except Exception as e:
            logger.debug(e)
            logger.error(f"Error opening token service: {e}")

    def close_service(self):
        """
        Python wrapper for the C++ call using ctypes this method should return a handle to the process that manages
        tokens using the sdauto32.dll typelib
        """
        svc_close = self.process.CloseTokenService
        if platform.architecture()[0] == "64bit":
            logger.debug("Setting return type of OpenTokenService to c_int64")
            svc_close.restype = c_int64
        else:
            logger.debug("Setting return type of OpenTokenService to c_int64")
            svc_close.restype = c_int

        logger.debug("Setting args for CloseTokenService to c_long")
        svc_close.argtypes = [c_long,]

        try:
            # > 0 means success
            logger.debug("Calling CloseTokenService function with ctypes")
            if svc_close(self.lTokenServiceHandle) > 0:
                self.lTokenServiceHandle = None
                logger.debug("Token Service closed")
            else:
                logger.debug("Could not close token service.")
                self.get_token_error()

        except Exception as e:
            logger.debug(e)
            logger.error("Error closing service.")

    def enum_tokens(self) -> DWORD:
        """
        Python wrapper for the C++ call using ctypes this method should return a handle to the process that manages
        tokens using the sdauto32.dll typelib
        Get the number of tokens registered with the token service by enumerating. The lTokens var gets filled with a
        count. self.lDefaultToken gets filled with the index of the system default token in the returned array. The
        default token will be used for all deprecated calls that don't pass in a serial. The default can be changed
        with SelectToken

        :return: DWORD
        """
        svc_enum = self.process.EnumToken

        if platform.architecture()[0] == "64bit":
            logger.debug("Setting return type of EnumToken to c_int64")
            svc_enum.restype = c_int64
        else:
            logger.debug("Setting return type of EnumToken to c_int64")
            svc_enum.restype = c_int

        logger.debug("Setting arguments for EnumToken to LONG, LPLONG, LPLONG,LPVOID, LPDWORD")
        svc_enum.argtypes = [LONG, LPLONG, LPLONG, LPVOID, LPDWORD, ]
        # See if there are any registered tokens and set up the buffer
        try:
            logger.debug("Calling EnumToken function with ctypes to get the buffer size first")
            svc_enum(
                self.lTokenServiceHandle,
                self.lTokens,  # lTokens gets filled with token count. Don't provide a token array pointer yet
                self.lDefaultToken,
                0,  # Send 0 the first time in case there are no tokens to grab
                self.dwBuffersize
            )

        except Exception as e:
            logger.debug(e)
            logger.error("Error getting number of tokens.")

        # if we got here, we didn't receive an error from the token service. The token count
        # is now stored in lTokens as a LONG
        if self.lTokens.value <= 0:
            logger.warning("No tokens were registered according to EnumToken")
            self.get_token_error()
            return DWORD(0)

    def get_tokens(self) -> List[Token]:
        """
        Python wrapper for the C++ call using ctypes. This method should return a list of tokeninfo objects from the
        process as tokeninfo structs from c++. The python methods will parse these structs into usable Token class
        objects. The number of tokens registered with the token service was obtained by EnumToken. The self.lTokens
        var contains a count. self.lDefaultToken gets filled with the index of the system default token in the returned
        array. The default token will be used for all deprecated calls that don't pass in a serial. The default can be
        changed with the SelectToken method if I ever implement it.
        :return: DWORD
        """

        # First, see if there are any registered tokens. If not, return an empty dict
        logger.debug("Checking to see if there is a token count before getting tokens. Was EnumToken successful?")
        if self.lTokens.value == 0:
            logger.debug("There are no registered tokens.")
            return []

        # Create an array of token structs
        logger.debug("Tokens are registered. Create a pointer to an array of empty TOKENBASICINFO structs to pass in")
        lpTokens = (token_basic_info * self.lTokens.value)()
        tokens = []

        # There are lTokens # of tokens. Get them in an array. The dwBuffersize has to have been set
        # previously, which is done during init in the enum_tokens() call. If dwBuffer points to a
        # null DWORD, the function will return zero/false and fill dwBuffersize with the correct size
        svc_enum = self.process.EnumToken

        if platform.architecture()[0] == "64bit":
            logger.debug("Setting return type of EnumToken to c_int64")
            svc_enum.restype = c_int64
        else:
            logger.debug("Setting return type of EnumToken to c_int64")
            svc_enum.restype = c_int

        svc_enum.argtypes = [LONG, LPLONG, LPLONG, LPVOID, LPDWORD, ]
        logger.debug(f"Setting arguments for EnumToken to {svc_enum.argtypes}")

        # See if there are any registered tokens and set up the buffer
        try:
            logger.debug("Calling EnumToken function with ctypes to get the tokens second")

            if svc_enum(
                    self.lTokenServiceHandle,
                    byref(self.lTokens),
                    byref(self.lDefaultToken),
                    byref(lpTokens),
                    byref(self.dwBuffersize)
            ) > 0:
                logger.info("{} tokens found:".format(self.lTokens.value))
            else:
                logger.error("Did not find any tokens.")
                self.get_token_error()

        except Exception as e:
            logger.debug(e)
            logger.error("Error getting tokens.")
            self.get_token_error()
            return []

        # Grab the token basic info for each token into a Token array. All stauto32 strings are utf-8
        logger.debug("Parsing tokenbasicinfo structs frrom list into python dicts")
        for x, token in enumerate(lpTokens):
            logger.debug("Building token data dict from ctypes return data")
            token_data = {}
            token_data.update({'token_service': self})
            logger.debug(f"Added token service (self) {self}")
            token_data.update({'username': token.username.decode('utf-8')})
            logger.debug(f"Added username {token_data['username']}")
            token_data.update({'device_id': token.deviceID})
            logger.debug(f"Added device_id {token_data['device_id']}")
            token_data.update({'descriptor': token.descriptor})
            logger.debug(f"Added descriptor {token_data['descriptor']}")
            serial = token.serial_number.decode('utf-8')
            logger.debug(f"Added serial number {serial}")

            # Check to see if we're the default token
            if self.lDefaultToken.value == x:
                logger.info("Identified the default token")
                token_data.update({'is_default': True})
            else:
                logger.debug("This token is not the default")
                token_data.update({'is_default': False})

            logger.debug(f"Append new token {serial} to token list")
            tokens.append(Token(serial, token_data))

        logging.debug(f"Return the {self.lTokens.value}-token list to the calling process")
        return tokens

    def get_default_token(self) -> Token:
        """
        Try to get the default token handle based on the default token index
        :return: Token
        """
        if self.lTokens.value:
            logger.debug(f"Returning the {self.lTokens.value} token object as default")
            return self.tokens[self.lDefaultToken.value]

        logging.warning("There was not default token recognized by the SD Process.")

    def get_token_current_code(self, serial: str, pin_style: str, pin: str = '') -> Tuple[ByteString, Any, int]:
        # The Pièce de résistance of this lib. Get the current code that would be displayed on the token screen
        # return a tuple of code + time-left.

        # When using PINs with get_token_current_code, the passcode returned will vary based on the type of token.
        # There are three different types:
        #   PINPad-style - With this type of token, the numeric PIN is mixed or rolled into the tokencode. The passcode
        #   will be the same length as the tokencode (typically 6 or 8 digits).

        #   Fob-style - With this type of token, the alphanumeric PIN is prepended to the tokencode which can result in
        #   a passcode with a maximum length of 16 (8 characters for the PIN and 8 characters for the tokencode).

        #   PINless - With this type of token, the PIN is ignored if it is passed in, and the passcode will always be
        #   the same as the tokencode.

        logger.debug(f"Pin style is {pin_style}")
        if self.pin_style == "Fob-style":
            passcode_length = self.pin_length + self.tokencode_length
        else:
            passcode_length = self.pin_length + self.tokencode_length

        logger.debug(f"Passcode length is now {passcode_length}")

        logger.debug("Creating string buffers for passcode and pincode argument vars")

        # ctypes strings are bytes
        chPASSCODE = create_string_buffer(passcode_length)
        chPRN = create_string_buffer(self.tokencode_length)
        chPIN = c_char_p(pin.encode('utf-8'))
        lTimeLeft = LONG()

        svc_get_code = self.process.GetCurrentCode

        if platform.architecture()[0] == "64bit":
            logger.debug("Setting return type of GetCurrentCode to c_int64")
            svc_get_code.restype = c_int64
        else:
            logger.debug("Setting return type of GetCurrentCode to c_int64")
            svc_get_code.restype = c_int

        svc_get_code.argtypes = [LONG, LPCSTR, LPCSTR, LPLONG, LPSTR, LPSTR,]
        logger.debug(f"Setting arguments for GetCurrentCode to {svc_get_code.argtypes}")

        logger.debug("Calling GetCurrentCode with ctypes.")
        try:
            if self.process.GetCurrentCode(
                self.lTokenServiceHandle,
                serial.encode("utf-8"),
                chPIN,
                byref(lTimeLeft),
                chPASSCODE,
                chPRN
            ) > 0:
                logger.info("Successfully retrieved the code.")
            else:
                logger.error("We did not successdully call the GetCurrentCode function")

        except Exception as e:
            logger.debug(e)
            logger.error("Error getting token code.")
            self.get_token_error()

        # On pinless tokens, PASSCODE and PRN will be the same
        logger.debug(f"Returning the passcode:{chPASSCODE.value}, tokencode: {chPRN.value}, and time left: {lTimeLeft}")
        return chPASSCODE.value.decode('utf-8'), chPRN.value.decode('utf-8'), lTimeLeft.value

    def can_get_next_code(self):
        """
        Not Yet Implemented
        """
        pass


    def get_token_next_code(self, serial: str, pin: str = ''):
        # get the next passcode or tokencode (PRN) from a specified token
        # return a named tuple of passcode, tokencode, time-left
        # When using PINs with get_token_next_code, the passcode returned will vary based on the type of token.
        # There are three different types:
        #   PINPad-style - With this type of token, the numeric PIN is mixed or rolled into the tokencode. The passcode
        #   will be the same length as the tokencode (typically 6 or 8 digits).

        #   Fob-style - With this type of token, the alphanumeric PIN is prepended to the tokencode which can result in
        #   a passcode with a maximum length of 16 (8 characters for the PIN and 8 characters for the tokencode).

        #   PINless - With this type of token, the PIN is ignored if it is passed in, and the passcode will always be
        #   the same as the tokencode.

        if self.pin_style == "Fob-style":
            logger.debug(
                f"Fob-style token detected. Setting passcode length to pin_length {self.pin_length} +"
                f" tokencode length {self.tokencode_length}"
            )
            passcode_length = self.pin_length + self.tokencode_length
        else:
            logger.debug("PINLess or PINPad token. Tokencode and passcode length are equal.")
            passcode_length = self.tokencode_length

        chPASSCODE = create_string_buffer(passcode_length)
        chPRN = create_string_buffer(self.tokencode_length)

        # ctypes strings are bytes
        chPIN = c_char_p(pin.encode('utf-8'))
        lTimeLeft = LONG()

        svc_get_next = self.process.GetNextCode

        if platform.architecture()[0] == "64bit":
            logger.debug("Setting return type of GetNextCode to c_int64")
            svc_get_next.restype = c_int64
        else:
            logger.debug("Setting return type of GetNextCode to c_int64")
            svc_get_next.restype = c_int

        svc_get_next.argtypes = [LONG, LPLONG, LPLONG, LPVOID, LPDWORD, LPDWORD]
        logger.debug(f"Setting arguments for GetNextCode to {svc_get_next.argtypes}")

        logger.debug("Calling GetNextCode with ctypes.")


        try:
            self.process.GetNextCode(
                self.lTokenServiceHandle,
                serial.encode("utf-8"),
                chPIN,
                byref(lTimeLeft),
                chPASSCODE,
                chPRN
            )
        except Exception as e:
            logger.debug(e)
            logger.error("Error getting next token code.")
            self.get_token_error()
        # On pinless tokens, PASSCODE and PRN will be the same
        return chPASSCODE.value.decode('utf-8'), chPRN.value.decode('utf-8'), lTimeLeft.value

    def get_token_expiration_date(self, serial):
        # Get the expiration date of the token with this serial number
        # The date is returned as a CKDATE struct
        expiration_date = ck_date()

        # Get the struct and parse it - Should I use datetime library here instead of a string?
        try:
            # > 0 means success
            if self.process.GetTokenExpirationDate(
                    self.lTokenServiceHandle,
                    serial.encode('utf-8'),
                    byref(expiration_date)
            ) > 0:
                logger.info("GetTokenExpirationDate: Got token expiration date struct")
                month: str = bytes(expiration_date.month).decode('utf-8')
                day: str = bytes(expiration_date.day).decode('utf-8')
                year: str = bytes(expiration_date.year).decode('utf-8')
                printable_date: date = date(int(year), int(month), int(day))
            else:
                self.get_token_error()
                logger.warning("GetTokenExpirationDate returned 0")
                printable_date = None
        except Exception as e:
            logger.debug(e)
            logger.error("Error getting token expiration date.")
            self.get_token_error()
            printable_date = None

        return printable_date

    def get_token_error(self):
        # Get any token error. Create a TOKENERRORINFO struct
        token_error = token_error_info()

        # get a pointer to use in the dll call
        lp_token_error = pointer(token_error)

        # Call the dll function, pass in the struct pointer to get filled. > 0 is success
        if self.process.GetTokenError(
                self.lTokenServiceHandle,
                lp_token_error
        ) > 0:
            if lp_token_error and token_error:
                # Dereference the pointer/get contents
                content = lp_token_error.contents
                if content.error != 0:
                    err_number = INT(content.error).value
                    err_string = content.error_string.decode('utf-8')
                    detailed_error_string = content.detailed_error_string.decode('utf-8')
                    logger.debug(
                        f"Last Token Error from SDProcess: {err_number}: {TokenError(err_number).name}"
                        f"{err_string}\n{detailed_error_string}"
                    )
                else:
                    logger.debug("No errors reported from SDProcess.")
            else:
                logger.debug("SDProcess Returned NULL pointer for last token error.")
        else:
            logger.debug("SD Process last token error has no content.")

    def __del__(self):
        """
        Class destructor - try to gracefully close the sd service since we're opening it via ctypes. Python may
        clean up the pointer and leave a ghost process running? Not sure how it works, but this seems safe. SDK
        says to always close it in C++ apps.
        :return:
        """
        logger.debug("Destructor called. Attempting graceful close of SDProcess")
        try:
            self.close_service()
        except Exception as e:
            pass


class NoProcessError(Exception):
    pass