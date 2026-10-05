"""Required external service declaration.

A plugin that needs a separate process (a search server, a cache) declares it
in its static `PluginDescriptor.required_services`. The composer records the
declaration in the lock, generates the deployment inputs that run it, and
wires its address and secret reference into the plugin's own configuration.
Nothing here starts or talks to a service; this is metadata only, readable
before `django.setup()` like the rest of the descriptor.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass

SERVICE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")

ADDRESS_CONFIG_KEY = "address"
SECRET_CONFIG_KEY = "secret"
_CONFIG_KEYS = frozenset({ADDRESS_CONFIG_KEY, SECRET_CONFIG_KEY})


def is_pinned_image(image: str) -> bool:
    """Whether `image` carries a digest or a tag other than `latest`."""
    if "@sha256:" in image:
        return True
    name = image.rsplit("/", 1)[-1]
    if ":" not in name:
        return False
    return name.rsplit(":", 1)[1] not in {"", "latest"}


@dataclass(frozen=True, slots=True)
class RequiredService:
    id: str
    """Compose service name and address host, e.g. `meilisearch`."""

    purpose: str
    image: str
    """Container image reference pinned by tag or digest, never `latest`."""

    port: int
    health_check: tuple[str, ...]
    """Command run inside the container; exit 0 means healthy."""

    config_keys: Mapping[str, str]
    """Maps `address` (required) and optionally `secret` to field names of the
    declaring plugin's `config_schema`."""

    data_path: str | None = None
    """Container path to persist on a named volume; `None` means stateless."""

    secret_env: str | None = None
    """Environment variable the container reads its access key from. Required
    when `config_keys` names a `secret`."""

    def __post_init__(self) -> None:
        if not SERVICE_ID_PATTERN.fullmatch(self.id):
            raise ValueError(
                f"required service id {self.id!r} must be lowercase letters, "
                "digits and dashes, starting with a letter"
            )
        if not is_pinned_image(self.image):
            raise ValueError(
                f"required service {self.id!r} image {self.image!r} must be "
                "pinned by a tag other than 'latest' or by a digest"
            )
        if not 0 < self.port < 65536:
            raise ValueError(f"required service {self.id!r} port is out of range")
        if not self.health_check:
            raise ValueError(f"required service {self.id!r} needs a health check")
        unknown = set(self.config_keys) - _CONFIG_KEYS
        if unknown or ADDRESS_CONFIG_KEY not in self.config_keys:
            raise ValueError(
                f"required service {self.id!r} config_keys must name "
                f"{ADDRESS_CONFIG_KEY!r} and optionally {SECRET_CONFIG_KEY!r}"
            )
        if (SECRET_CONFIG_KEY in self.config_keys) != (self.secret_env is not None):
            raise ValueError(
                f"required service {self.id!r} must set secret_env exactly "
                f"when config_keys names {SECRET_CONFIG_KEY!r}"
            )
        if self.data_path is not None and not self.data_path.startswith("/"):
            raise ValueError(f"required service {self.id!r} data_path must be absolute")
