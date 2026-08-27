from dmr.openapi import OpenAPIConfig
from dmr.settings import Settings

DMR_SETTINGS = {
    Settings.openapi_config: OpenAPIConfig(title="Atlas API", version="0.1.0"),
    Settings.openapi_examples_seed: 1,
    # runtime-failure-isolation spec: an unhandled exception in any Core or
    # plugin controller gets a clean typed 500 instead of a raw traceback.
    Settings.global_error_handler: (
        "server.apps.plugins.error_handling.global_error_handler"
    ),
}
