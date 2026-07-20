from __future__ import annotations

from application.portal.domain.value_objects.access_status import (
    ACCESS_STATUS_APPROVED,
    ACCESS_STATUS_PENDING,
    ACCESS_STATUS_REJECTED,
)
from application.portal.models import UserAccessRequest


def test_access_status_constants_match_orm_choices():
    assert ACCESS_STATUS_PENDING == UserAccessRequest.Status.PENDING
    assert ACCESS_STATUS_APPROVED == UserAccessRequest.Status.APPROVED
    assert ACCESS_STATUS_REJECTED == UserAccessRequest.Status.REJECTED
