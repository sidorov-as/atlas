"""Password validators derived from generated Atlas policy."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class MaximumLengthValidator:
    def __init__(self, max_length: int = 128) -> None:
        self.max_length = max_length

    def validate(self, password: str, user=None) -> None:
        if len(password) > self.max_length:
            raise ValidationError(
                _(
                    "This password is too long. It must contain at most "
                    "%(max_length)d characters."
                ),
                code="password_too_long",
                params={"max_length": self.max_length},
            )

    def get_help_text(self) -> str:
        return _(
            "Your password must contain at most %(max_length)d characters."
        ) % {"max_length": self.max_length}
