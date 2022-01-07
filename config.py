from os import environ

# Keys for access to the Princeton API
DIRECTORY_BASE_URL = "https://api.princeton.edu:443/active-directory/1.0.3"
USERS = "/users/basic"
ACCESS_TOKEN = ""
CONSUMER_KEY = environ['CONSUMER_KEY']
CONSUMER_SECRET = environ['CONSUMER_SECRET']
REFRESH_TOKEN_URL = "https://api.princeton.edu:443/token"

DATABASE_URL = environ['DATABASE_URL'][:8]+'ql'+environ['DATABASE_URL'][8:]
