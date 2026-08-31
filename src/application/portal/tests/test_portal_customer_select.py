from __future__ import annotations

import pytest
from django.template.loader import render_to_string


@pytest.mark.parametrize(
    ("context", "expected"),
    [
        (
            {
                "field_name": "customer_code",
                "label": "得意先",
                "variant": "receipt",
                "customers": [{"custCode": "101", "custName": "サンプル得意先A"}],
                "selected_value": "101",
                "required": True,
            },
            [
                'class="portal-customer-field portal-customer-field--receipt"',
                'class="portal-customer-select portal-customer-select--receipt"',
                "101 - サンプル得意先A",
            ],
        ),
        (
            {
                "field_name": "custCode",
                "label": "得意先",
                "variant": "gonen",
                "customers_api": "/api/gonenkukumi/customers",
                "customers": [{"custCode": "191", "custName": "サンプル得意先E"}],
                "selected_value": "191",
                "select_id": "custCode",
            },
            [
                'class="portal-customer-field portal-customer-field--gonen"',
                'class="portal-customer-select portal-customer-select--gonen"',
                'id="custCode"',
                "191 - サンプル得意先E",
            ],
        ),
        (
            {
                "field_name": "customer_code",
                "customers": [{"custCode": "101", "custName": "サンプル得意先A"}],
                "selected_value": "101",
                "required": True,
            },
            [
                'name="customer_code"',
                'class="portal-customer-select"',
                "得意先",
                'value="101" selected',
                "101 - サンプル得意先A",
            ],
        ),
        (
            {
                "field_name": "direct_delivery_customer_code",
                "label": "直送先得意先コード",
                "customers": [{"custCode": "102", "custName": "サンプル得意先B"}],
                "empty_label": "なし",
            },
            [
                ">なし</option>",
                "102 - サンプル得意先B",
            ],
        ),
        (
            {
                "field_name": "direct_delivery_customer_code",
                "variant": "receipt",
                "customers": [{"custCode": "102", "custName": "サンプル得意先B"}],
                "selected_value": "102",
                "hide_label": True,
            },
            [
                'class="portal-customer-select portal-customer-select--receipt"',
                "102 - サンプル得意先B",
            ],
        ),
        (
            {
                "field_name": "custCode",
                "label": "得意先",
                "customers_api": "/api/gonenkukumi/customers",
                "selected_value": "191",
                "select_id": "custCode",
            },
            [
                'id="custCode"',
                'data-customers-api="/api/gonenkukumi/customers"',
                'value="191" selected',
            ],
        ),
    ],
)
def test_customer_select_include_renders_shared_markup(context, expected):
    html = render_to_string("includes/customer_select.html", context)

    for snippet in expected:
        assert snippet in html


def test_customer_select_hide_label_omits_label_wrapper():
    html = render_to_string(
        "includes/customer_select.html",
        {
            "field_name": "direct_delivery_customer_code",
            "variant": "receipt",
            "customers": [{"custCode": "102", "custName": "サンプル得意先B"}],
            "selected_value": "102",
            "hide_label": True,
        },
    )

    assert 'class="portal-customer-field' not in html
    assert 'class="portal-customer-select portal-customer-select--receipt"' in html
