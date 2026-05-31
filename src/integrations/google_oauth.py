from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from src.core.config import settings

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',  # чтобы узнать email/google_id
]

def get_authorization_url(state: str = None) -> tuple[str, str]:
    #Создаёт Flow и возвращает URL авторизации и state
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        state=state,
    )

    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    authorization_url, state = flow.authorization_url(
        access_type='offline',          # чтобы получить refresh_token
        include_granted_scopes='true',
        prompt='consent',               # чтобы refresh_token выдавался каждый раз
    )
    return authorization_url, state

def exchange_code(code: str) -> Credentials:
   #Временный код на объект Credentials, содержащий токены
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )

    flow.fetch_token(code=code)
    credentials = flow.credentials
    return credentials