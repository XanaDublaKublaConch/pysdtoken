from enum import Enum
import platform
from ctypes import c_char, c_int, c_long, c_ubyte
from ctypes import Structure

if platform.system() == "Windows":
    from ctypes.wintypes import DWORD, INT

elif platform.system() == "Darwin":
    DWORD = c_long
    INT = c_int

else:
    exit(f"Unsupported platform: {platform.system()}")


# A struct to hold token information
class struct_tagTOKENBASICINFO(Structure):
    _pack_ = 1  # source:False
    _fields_ = [
        ('dwSize', DWORD),
        ('serial_number', c_char * 24),
        ('username', c_char * 24),
        ('deviceID', c_char * 24),
        ('descriptor', c_char * 48),
    ]


token_basic_info = struct_tagTOKENBASICINFO


# A struct to hold token error information
class struct_tagTOKENERRORINFO(Structure):
    _pack_ = 1  # source:False
    _fields_ = [
        ('error', c_int),
        ('error_string', c_char * 24),
        ('detailed_error_string', c_char * 64),
    ]


token_error_info = struct_tagTOKENERRORINFO


# A struct to hold dates
class struct_CK_DATE(Structure):
    _pack_ = 1  # source:False
    _fields_ = [
        ('year', c_ubyte * 4),
        ('month', c_ubyte * 2),
        ('day', c_ubyte * 2),
    ]

    def __repr__(self):
        return '({0}/{1}/{2}'.format(self.day, self.month, self.year)


ck_date = struct_CK_DATE


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
