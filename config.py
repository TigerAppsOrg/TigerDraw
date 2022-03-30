from os import environ

from dotenv import load_dotenv

load_dotenv()
# Keys for access to the Princeton API
DIRECTORY_BASE_URL = (
    "https://api.princeton.edu:443/active-directory/1.0.3"
)
USERS = "/users/basic"
ACCESS_TOKEN = ""


# print("*test", environ["HOME"])
CONSUMER_KEY = environ["CONSUMER_KEY"]
# b"\xe7\xa3\x1c\xf2\n\xe9\xb6\xd0\xcd\xbcI\xa9\x14\x8a\x91\x86"

CONSUMER_SECRET = b"\xe7\xa3\x1c\xf2\n\xe9\xb6\xd0\xcd\xbcI\xa9\x14\x8a\x91\x86"  # environ["CONSUMER_SECRET"]
REFRESH_TOKEN_URL = "https://api.princeton.edu:443/token"

DATABASE_URL = environ["DATABASE_URL"]