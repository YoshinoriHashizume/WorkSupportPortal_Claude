from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_real_vendor_lookup(monkeypatch):
    """設定画面・設定 API のテストが実 Oracle（仕入先マスタ）に接続しないよう、既定では接続できない扱いにする。

    仕入先名を使うテストは `wiring.lookup_vendor_names` を個別に差し替える（spec/12 test-design §5.2）。
    """
    from application.inventory_order_alert.domain.value_objects.errors import VendorLookupUnavailableError
    from application.inventory_order_alert.interfaces import wiring

    def unavailable(codes):
        raise VendorLookupUnavailableError()

    monkeypatch.setattr(wiring, "lookup_vendor_names", unavailable, raising=False)
