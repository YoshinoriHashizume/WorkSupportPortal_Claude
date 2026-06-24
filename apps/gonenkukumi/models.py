from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class GonenKukumiSearchHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="gonenkukumi_histories")
    executed_at = models.DateTimeField(auto_now_add=True)
    cust_code = models.CharField(max_length=3)
    cust_item = models.CharField(max_length=80, blank=True)
    option_change = models.CharField(max_length=20, default="*")
    year_month = models.CharField(max_length=7)

    class Meta:
        ordering = ["-executed_at"]
        indexes = [models.Index(fields=["user", "-executed_at"], name="gonenkukumi_user_exe_idx")]

    def to_api_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "executedAt": self.executed_at.isoformat(),
            "custCode": self.cust_code,
            "custItem": self.cust_item,
            "optionChange": self.option_change,
            "yearMonth": self.year_month,
        }
