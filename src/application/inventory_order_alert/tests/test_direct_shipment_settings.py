"""直送仕入先（V-240）の保存・仕入先名の解決（AppSettingsUseCase）。

spec/12_direct-shipment-exclusion test-design.md TC-DSE-A-010〜018。DB・基幹は使わない（スタブ）。
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.direct_shipment import DirectShipmentSuppliers, VendorName
from application.inventory_order_alert.domain.value_objects.errors import VendorLookupUnavailableError
from application.inventory_order_alert.use_cases.app_settings import AppSettingsUseCase


class _Store:
    """設定の読込・保存スタブ。保存の呼出しを記録する。"""

    def __init__(self, codes: list[str]) -> None:
        self.current = AppSettings(direct_shipment_suppliers=DirectShipmentSuppliers.parse(codes))
        self.saved: list[dict[str, object]] = []

    def load(self) -> AppSettings:
        return self.current

    def save(self, **kwargs: object) -> AppSettings:
        self.saved.append(kwargs)
        suppliers = kwargs.get("direct_shipment_suppliers") or self.current.direct_shipment_suppliers
        self.current = replace(
            self.current,
            warning_days=kwargs["warning_days"],
            direct_shipment_suppliers=suppliers,
        )
        return self.current


class _Lookup:
    def __init__(self, names: dict[str, str] | None = None, *, unavailable: bool = False) -> None:
        self.names = names or {}
        self.unavailable = unavailable
        self.calls: list[list[str]] = []

    def __call__(self, codes: list[str]) -> dict[str, str]:
        self.calls.append(list(codes))
        if self.unavailable:
            raise VendorLookupUnavailableError()
        return {code: name for code, name in self.names.items() if code in codes}


def _use_case(store: _Store, lookup: _Lookup) -> AppSettingsUseCase:
    return AppSettingsUseCase(store.load, store.save, lookup_vendor_names=lookup)


def test_a010_only_new_codes_are_checked_then_saved():
    store = _Store(["9100", "9200"])
    lookup = _Lookup({"9100": "丸栄豊田", "9200": "テクノス工場", "9250": "丸栄豊田（福岡）"})

    _use_case(store, lookup).save_view({"directShipmentSupplierCodes": ["9100", "9200", "9250"]})

    assert lookup.calls[0] == ["9250"]
    assert store.saved[0]["direct_shipment_suppliers"].codes == ("9100", "9200", "9250")


def test_a011_unknown_code_is_not_saved():
    store = _Store(["9100"])
    lookup = _Lookup({})

    with pytest.raises(ValueError, match="仕入先マスタに存在しない仕入先コードです: 9999"):
        _use_case(store, lookup).save_view({"directShipmentSupplierCodes": ["9100", "9999"]})

    assert store.saved == []


def test_a012_unavailable_lookup_is_not_saved():
    store = _Store(["9100"])
    lookup = _Lookup(unavailable=True)

    with pytest.raises(VendorLookupUnavailableError):
        _use_case(store, lookup).save_view({"directShipmentSupplierCodes": ["9100", "9250"]})

    assert store.saved == []


def test_a013_removing_codes_does_not_query_vendor_master():
    store = _Store(["9100", "9200"])
    lookup = _Lookup(unavailable=True)

    result = _use_case(store, lookup).save_view({"directShipmentSupplierCodes": ["9100"]})

    assert lookup.calls == [["9100"]]  # 応答の名前解決だけ（失敗しても保存は成功）
    assert store.saved[0]["direct_shipment_suppliers"].codes == ("9100",)
    assert result["settings"]["directShipmentSupplierCodes"] == ["9100"]
    assert result["directShipmentSuppliers"] == [{"code": "9100", "name": "", "status": "unavailable"}]


def test_a014_save_without_direct_suppliers_succeeds_while_lookup_is_down():
    store = _Store(["9100"])
    lookup = _Lookup(unavailable=True)

    result = _use_case(store, lookup).save_view({"warningDays": 100})

    assert store.saved[0]["warning_days"] == 100
    assert result["settings"]["directShipmentSupplierCodes"] == ["9100"]


def test_a015_registered_code_missing_from_master_is_kept_without_check():
    store = _Store(["9100", "8888"])
    lookup = _Lookup({"9100": "丸栄豊田"})

    _use_case(store, lookup).save_view({"directShipmentSupplierCodes": ["9100", "8888"]})

    assert store.saved[0]["direct_shipment_suppliers"].codes == ("8888", "9100")
    # 保存前の実在確認は呼ばれない（呼ばれたのは応答の名前解決 1 回だけ）
    assert lookup.calls == [["8888", "9100"]]


def test_a016_vendor_names_distinguish_found_and_not_found():
    store = _Store(["9100", "8888"])
    lookup = _Lookup({"9100": "丸栄豊田"})

    view = _use_case(store, lookup).load_view()

    assert view["directShipmentSuppliers"] == [
        VendorName("8888", "", "not_found").to_payload(),
        VendorName("9100", "丸栄豊田", "found").to_payload(),
    ]


def test_a017_view_is_returned_even_if_lookup_is_unavailable():
    store = _Store(["9100", "9250"])
    lookup = _Lookup(unavailable=True)

    view = _use_case(store, lookup).load_view()

    assert [entry["status"] for entry in view["directShipmentSuppliers"]] == ["unavailable", "unavailable"]
    assert view["settings"]["directShipmentSupplierCodes"] == ["9100", "9250"]


def test_a018_save_response_contains_saved_codes_and_names():
    store = _Store(["9100", "9200"])
    lookup = _Lookup({"9100": "丸栄豊田", "9200": "テクノス工場", "9250": "丸栄豊田（福岡）"})

    result = _use_case(store, lookup).save_view({"directShipmentSupplierCodes": ["9100", "9200", "9250"]})

    assert result["settings"]["directShipmentSupplierCodes"] == ["9100", "9200", "9250"]
    assert result["directShipmentSuppliers"][2] == {"code": "9250", "name": "丸栄豊田（福岡）", "status": "found"}


def test_load_view_without_codes_does_not_query():
    store = _Store([])
    lookup = _Lookup(unavailable=True)

    view = _use_case(store, lookup).load_view()

    assert view["directShipmentSuppliers"] == []
    assert lookup.calls == []
