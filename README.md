# pysdtoken
A pythonic (?) ctypes wrapper for RSA SecurID Tokens
I am somewhat new to Python and barely intermediate in C-style languages, so this was my attempt to fill a gap that I saw. I could not find a way to access the Soft Token using python, but lots of VPN vendors use the vendor SDK to do what I wanted to do. 

## Usage
You'll need a handle to the SDProcess first. This is the token service that sduato32.dll access for everything. Behind the scenes, all token requests are calling the sd process with a token serial as the argument.
```python
from pysdtoken import SDProcess
sd = SDProcess()
```


### Optionally set the logger level
```python
sd = SDProcess(log_level='DEBUG')
```
Be forewarned: DEBUG level is going to flood you with information. This was mainly to compensate for my lack of skill/knowledge. Sorry. :grinning:

SDProcess can also take a dll path using the dll named param. It will be loaded with the ctypes windll or cdll call, so if a path is given, it try loading from the given absolute path. If a dll file is given, it will try using the current dll search path.

### get the default token as a Token object
The sd process assigns a token as the "default token". I think the "default token" concept was used for the deprecated calls that did not require a serial number as an argument. As far as I can tell, the GUI version of the soft token considers the selected token to be the default. I'm not sure why you would need this in the python library. If you have one token, this function will return your token object.
```python
my_token = sd.get_default_token()
```
If you have multiple tokens, just check the list of tokens in the SDProcess object:
```python
sd.tokens
[Token(000123456789, PINless), Token(000111122311, PINless)*, Token(000234567654, PINless), Token(12343212345, PINless)]
```
The default token is marked with a *. If you want a different token, just grab it from the list:
```python
my_token2 = sd.tokens[0]
>>> my_token2
Token(000123456789, PINless)
```
 You can also get a token by its serial number. I don't have a use case for this, but...I dunno.
 ```python
specific_token = sd.get_token_by_serial('1234567890')
```

The SD Process also holds the last token error that occurred.
```python
>>> sd.get_token_error()
'Last Token Error from SDProcess: 17: ERROR_BUFFER_TOO_SMALL_ERROR'
```
It was useful while coding this library, but has limited use in any implementation I can think of.

### Close the process
You should close the process because the SDK says you should close the process. I'm sure python will clean up the pointer/handle, but I don't know if the process itself lingers.
```python
sd.close_service()
```
If you close the service, the token objects will cease working:
```python
>>> tkn = sd.get_default_token()
>>> sd.close_service()
>>> tkn.get_current_code()
ERROR:pysdtoken.pysdtoken:Error getting token code.
TokenInfo(passcode='', tokencode='', time_left=0)
```

If you do this accidentally, you can always create a new handle and set the sd process on the existing token object:
```python
>>> sd2 = SDProcess()
>>> tkn.set_sd_process(sd2)
>>> tkn.get_current_code()
TokenInfo(passcode='68545942', tokencode='68545942', time_left=9)

```
## Token
### get_current_code()
The function returns a named tuple of the passcode, tokencode, and time left. For pinless tokens:
- if you don't send a PIN, passcode and tokencode are identical
- if you send a PIN, passcode will be the tokencode with the pin prepended
```bash
>>>> my_token.get_current_code()
TokenInfo(passcode='80851855', tokencode='80851855', time_left=6)`
```

For tokens that require a pin before getting the code
```python
my_token.get_current_code(pin)
```

```python
mytoken.get_current_code('1234')
TokenInfo(passcode='123450484340', tokencode='50484340', time_left=7)
```
Get individual values from the token:
```python
>>> mytoken.get_current_code('1234').passcode
'123440269669'
>>> mytoken.get_current_code('1234').tokencode
'40269669'
>>> mytoken.get_current_code('1234').time_left
23
```

You can also get the expiration date of the token
```python
>>> tkn.get_expiration_date()
datetime.date(2035, 12, 31)
>>> print(tkn.get_expiration_date())
2035-12-31
>>>
```

Get a code from each using pin '1234'. I don't know why you would do this, but you can.
```python
>>> for token in sd.tokens:
...     token.get_current_code('1234').passcode
...
'66268520'
'123454816010'
'89718449'
'62015065'
>>>
```
### get_next_code()
Get the next code from the token. This is useful when you're in next token mode or testing your token. I've also implemented the backend "can_token_get_next_code()" method, but I have no idea why it's needed. I've never seen it return anything but True.
```python
>>> tkn.get_next_code()
TokenInfo(passcode='84226585', tokencode='84226585', time_left=7)
>>> tkn.can_get_next_code()
True
```

### Set the pin style
You can set the pin style for the token. It defaults to PINless because the info is not available from the sdauto process.
```python
>>> sd.valid_pin_styles
('PINless', 'PINPad-style', 'Fob-style')
>>> tkn.set_pin_style('PINPad-style')
>>> tkn.pin_style
'PINPad-style'
>>>
```
