from enum import Enum

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ValidationErrorEnum(Enum):
    def error(self, **params):
        params.setdefault("message", self.value)
        params.setdefault("code", self.name)
        return ValidationError(**params)


class SilenceError(ValidationErrorEnum):
    NOLABEL = _("Missing labels for silence.")
    GLOBALSILENCE = _("Unable to silence global rules with alertname alone.")
    STARTENDTIME = _("Both start and end are required.")
    STARTENDMISMATCH = _("Start time and end time are mismatched.")
    NOMATCHER = _("Missing matchers for silence.")
    NOSERVICEORPROJECTMATCHER = _("Silence must include a service or project matcher.")
