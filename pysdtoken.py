"""
Provide python access to th eRSA Soft Token Service
This module wraps the stauto32.dll calls using
ctypes to get the current code from the token
"""
from ctypes.wintypes import LONG
from ctypes import *

# A struct to hold token error information
class struct_tagTOKENERRORINFO(Structure):
    _pack = True  # source:False
    _fields = [
        ('error', c_int32),
        ('error_string', c_char * 24),
        ('detailed_error_string', c_char * 64),
    ]


token_error_info = struct_tagTOKENERRORINFO


# A struct to hold token information
class struct_tagTOKENBASICINFO(Structure):
    _pack = True  # source:False
    _fields = [
        ('dwSize', c_uint32),
        ('serialnumber', c_char * 24),
        ('username', c_char * 24),
        ('deviceID', c_char * 24),
        ('descriptor', c_char * 64),
    ]


token_basic_info = struct_tagTOKENBASICINFO


# A struct to hold dates
class struct_CK_DATE(Structure):
    _pack = True  # source:False
    _fields = [
        ('year', c_ubyte * 4),
        ('month', c_ubyte * 2),
        ('day', c_ubyte * 2),
    ]


CKDATE = struct_CK_DATE


class Token():
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

    def get_expiration_dat(self, token_service):
        return token_service.get_token_expiration_date(self.serialnumber)

    def get_current_code(self, token_service):
        return token_service.get_token_current_code(self.serialnumber)

class SDProcess():

    tokens = []
    lTokens = LONG()

    def __init__(self):
        # Get the SD process
        try:
            self.process = OleDLL('stauto32.dll')
        except Exception as e:
            print(e)
            print("Error finding Soft Token service.")

        self.handle = LONG()
        self.lDefaultToken = LONG()
        self.open_service()
        # Populate lTokens and dwBuffersize
        self.dwBuffersize = self.count_tokens()
        print("DEBUG: There are {} tokens.".format(self.lTokens.value))
        # Populate the token dict
        self.tokens = self.get_tokens()

    def open_service(self):
        try:
            # > 0 means success and dwBuffersize is set
            if self.process.OpenTokenService(byref(self.handle)) > 0:
                print("DEBUG: Token service started, handle {}.".format(self.handle.value))
            else:
                print("No token service found!")
        except Exception as e:
            print(e)
            print("Error opening token service.")

    def close_service(self):
        try:
            # > 0 means success
            if self.process.CloseTokenService(byref(self.handle)) > 0:
                print("DEBUG: Token Service closed")
            else:
                print("Could not close token service.")
        except Exception as e:
            print(e)
            print("Error closing service.")

    def count_tokens(self):
        # See if there are any registered tokens and set up the buffer
        dwBuffersize = LONG()
        try:
            # lTokens gets filled with the token count. Don't provide a token array pointer yet
            # Send 0 the first time in case there are no tokens to grab
            self.process.EnumToken(self.handle, byref(self.lTokens), byref(self.lDefaultToken), 0, byref(dwBuffersize))
        except Exception as e:
            print(e)
            print("Error getting number of tokens.")
            return ''

        # if we got here, we didn't receive an error from the token service. The token count
        # is now stored in lTokens as a LONG
        if self.lTokens.value > 0:
            return dwBuffersize
        else:
            return ''

    def get_tokens(self):
        # Get the number of tokens registered with the token service by enumerating. The lTokens
        # var gets filled with a count. lDefaultToken gets filled with the index of the system
        # default token in the returned array

        # First, see if there are any registered tokens. If not, return an empty dict
        if self.lTokens.value == 0:
            print("There are no registered tokens.")
            return {}

        # Create an array of token structs
        lpTokens = (token_basic_info * self.lTokens.value)
        tokens = []

        # There are lTokens # of tokens. Get them in an array. The dwBuffersize has to have been set
        # previously, which is done during init in the count_tokens() call. If dwBuffer points to a
        # null DWORD, the function will return zero/false and fill dwBuffersize withthe correct size
        try:
            if self.process.EnumToken(self.handle, byref(self.lTokens), byref(self.lDefaultToken), byref(lpTokens),
                                      byref(self.dwBuffersize)) > 0:
                print("{} tokens found:".format(self.lTokens.value))
            else:
                print("Did not find any tokens.")

        except Exception as e:
            print(e)
            print("Error getting tokens.")
            return []

        # Grab the token basic info for each token into a Token array. All stauto32 strings are utf-8
        for x, token in enumerate(lpTokens):
            token_data = []
            token_data['serialnumber'] = token.serialnumber.decode("utf-8")
            token_data['username'] = token.username.decode("utf-8")
            token_data['deviceID'] = token.deviceID
            token_data['descriptor'] = token.descriptor
            if self.lDefaultToken.value == x:
                token_data['is_default'] = True
            else:
                token_data['is_default'] = False
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
        chPASSCODE = c_char_p("".encode("utf-8"))
        chPRN = c_char_p("".encode("utf-8"))
        lTimeLeft = LONG()
        try:
            self.process.GetCurrentCode(self.handle, serial.encode("utf-8"), pin,
                                        byref(lTimeLeft), chPASSCODE, chPRN)
        except Exception as e:
            print(e)
            print("Error getting token code.")
        # On pinless tokens, PASSCODE and PRN will be the same
        return (chPASSCODE.value.decode('utf-8'), chPRN.value.decode('utf-8'), lTimeLeft.value)

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
                token_expiration = None
        except Exception as e:
            print(e)
            print("Error getting token exiration date.")
            token_expiration = None

        return token_expiration