import sys

import uvicorn

from .app import create_app
from .config import Settings

try:
    application = create_app(Settings.from_env())
except ValueError:
    print('{"event":"invalid_configuration"}', file=sys.stderr)
    sys.exit(2)

if __name__ == "__main__":
    # Access logs contain paths/queries; disabled in favor of the sanitized allowlist logger.
    uvicorn.run(
        application,
        host="127.0.0.1",
        port=8000,
        access_log=False,
        log_level="critical",
        timeout_keep_alive=5,
        timeout_graceful_shutdown=5,
    )
