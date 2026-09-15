from api_secure import app
import chat_api

# The web application is the primary client. Telegram remains optional.
chat_api.register(app)

__all__ = ["app"]
