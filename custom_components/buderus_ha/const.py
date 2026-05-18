from __future__ import annotations

DOMAIN = "buderus_ha"

CONF_ACCESS_TOKEN = "access_token"
CONF_EXPIRES_AT = "expires_at"
CONF_GATEWAY_ID = "gateway_id"
CONF_REFRESH_TOKEN = "refresh_token"

DEFAULT_USER_AGENT = "DashApp/3.7.0 (iOS-Release)"
POINTT_BASE_URL = "https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1"

OAUTH_AUTHORIZE_URL = "https://singlekey-id.com/auth/connect/authorize"
OAUTH_CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
OAUTH_REDIRECT_URI = "com.buderus.tt.dashtt://app/login"
OAUTH_SCOPES = (
    "openid",
    "email",
    "profile",
    "offline_access",
    "pointt.gateway.claiming",
    "pointt.gateway.removal",
    "pointt.gateway.list",
    "pointt.gateway.users",
    "pointt.gateway.resource.dashapp",
    "pointt.castt.flow.token-exchange",
    "bacon",
    "hcc.tariff.read",
)
OAUTH_STYLE_ID = "tt_bud"
OAUTH_TOKEN_URL = "https://singlekey-id.com/auth/connect/token"

PLATFORMS = ["number", "sensor", "switch"]
