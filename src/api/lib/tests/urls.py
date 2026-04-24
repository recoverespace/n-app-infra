API_V1 = '/v1'
DEVICE_INIT = f'{API_V1}/devices/init'
DEVICE_MY = f'{API_V1}/devices/my'
DEVICE_REFRESH_TOKEN = f'{API_V1}/devices/token/refresh'

AUTH_ANONYMOUS = f'{API_V1}/auth/anonymous'
AUTH_FIREBASE = f'{API_V1}/auth/login'
AUTH_REFRESH_TOKEN = f'{API_V1}/auth/token/refresh'
AUTH_CENTRIFUGE_REFRESH_TOKEN = f'{API_V1}/auth/centrifuge/refresh/'
AUTH_DOMAIN_CHECK = f'{API_V1}/auth/domain-check'

USERS_ME = f'{API_V1}/users/me'
USERS_ME_SETTINGS = f'{API_V1}/users/me/settings'
USERS_ME_FACTS = f'{API_V1}/users/me/facts/'
USERS_DEVICE_SETTINGS = f'{API_V1}/users/me/device/settings'

TRACKERS = f'{API_V1}/trackers/'

CHATS = f'{API_V1}/chats/'
CHATS_CENTRIFUGE_INFO = f'{API_V1}/chats/centrifuge-info'