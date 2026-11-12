"""The portal: one page for the person who administers a decision server, served by the server itself.

    decision-server ENVIRONMENT.toml --http [--port 8000] --portal 8400 [--portal-host 127.0.0.1]
                    [--portal-public-origin URL] [--ask-backend openai|claude] [--ask-model M] [--ask-model-url U]

The page shows an environment's whole configuration and changes only its documents and its derived layer, each
change taking effect at once; sign in with the key in DECISION_PORTAL_KEY. Its Ask page talks to the server through a
model, showing every call and result.
"""
PORTAL_KEY_ENV = "DECISION_PORTAL_KEY"
LOOPBACK = ("127.0.0.1", "localhost", "::1")
MIN_KEY = 16        # decision-server sets no minimum for DECISION_SERVER_KEY, so this is the portal's own
