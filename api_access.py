import requests, base64, json, sys
import config


def get_access_token():
    kwargs = {"grant_type": "client_credentials"}
    req = requests.post(
        config.REFRESH_TOKEN_URL,
        data=kwargs,
        headers={
            "Authorization": "Basic "
            + base64.b64encode(
                bytes(config.CONSUMER_KEY + ":" + config.CONSUMER_SECRET, "utf-8")
            ).decode("utf-8")
        },
    )
    text = req.text
    response = json.loads(text)
    config.ACCESS_TOKEN = response["access_token"]


def check_is_undergrad(username):
    return True
    # get an updated access token
    # get_access_token()

    # # query for information
    # kwargs = {"uid": username}
    # req = requests.get(
    #     config.DIRECTORY_BASE_URL + config.USERS,
    #     params=kwargs if "kwargs" not in kwargs else kwargs["kwargs"],
    #     headers={"Authorization": "Bearer " + config.ACCESS_TOKEN},
    # )

    # json = req.json()
    # if len(json) == 0:
    #     return False
    # return True


if __name__ == "__main__":
    is_undergrad = check_is_undergrad(sys.argv[1])
    print(sys.argv[1], is_undergrad)
