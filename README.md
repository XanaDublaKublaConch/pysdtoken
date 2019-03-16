# pysdtoken
A pythonic (?) ctypes wrapper for RSA SecurID Tokens
I am somewhat new to Python and barely intermediate in C-style languages, so this was my attempt to fill a gap that I saw. I could not find a way to access the Soft Token using python, but lots of VPN vendors use the vendor SDK to do what I wanted to do. 

## Usage
```python
import pysdtoken

# Get a reference to the background token service. This sets the logger to WARNING level by default
sd = pysdtoken.SDProcess()

# Or set the logger level
sd = pysdtoken.SDProcess(log_level='DEBUG')

# SDProcess can also take a dll path using the dll named param

# get the default token as a Token object (I've never had more than one to test with)
my_token = sd.get_default_token()

# get_current_code() needs the token service handle
# the function returns a tuple of the passcode, tokencode, and time left
# For pinless tokens:
#   - if you don't send a PIN, passcode and tokencode are identical
#   - if you send a PIN, passcode will be the tokencode with the pin prepended
pc, tc, tl = my_token.get_current_code(sd)

# For tokens that require a pin before getting the code
# pin = '1234'  # you should really prompt for the pin
# pc, tc, tl = my_token.get_current_code(sd, pin)
print("PassCode: {0}\nToken Code: {1}\nTime Left: {2}".format(pc, tc, tl))

# You can also get the expiration date of the token
print("Expires: {}".format(my_token.get_expiration_date(sd))

# Get all of the registered tokens as a list of Token objects
tkns = sd.get_tokens()

# See the serial numbers
for x, token in enumerate(tkns):
    print("Token {0}: {1}".format(x, token.serialnumber))

# Get a code from each using pin '1234'
for token in tkns:
    print("Token {0}: {1}".format(token.serialnumber, token.get_current_code(sd, pin='1234')))
```
