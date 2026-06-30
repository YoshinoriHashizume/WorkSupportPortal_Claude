from __future__ import annotations

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

BUSINESS_APPS = (
    "gonenkukumi",
    "receipt_comparison",
    "inventory_order_alert",
    "asset_inventory",
    "shipment_trend",
    "portal",
    "identity",
)

LAYER_DIRS = ("domain", "usecase", "infrastructure")


def _python_files_under(relative: str) -> list[Path]:
    base = ROOT / relative
    if not base.exists():
        return []
    return sorted(path for path in base.rglob("*.py") if path.name != "__init__.py")


def _imports_in_file(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


@pytest.mark.parametrize("app_name", BUSINESS_APPS)
def test_app_has_clean_architecture_layers(app_name: str):
    app_root = ROOT / "apps" / app_name
    for layer in LAYER_DIRS:
        assert (app_root / layer).is_dir(), f"{app_name} missing {layer}/"
    assert (app_root / "composition.py").is_file(), f"{app_name} missing composition.py"


@pytest.mark.parametrize("app_name", BUSINESS_APPS)
def test_views_do_not_import_infrastructure(app_name: str):
    views_path = ROOT / "apps" / app_name / "views.py"
    if not views_path.is_file():
        pytest.skip(f"{app_name} has no views.py")
    imports = _imports_in_file(views_path)
    forbidden = f"apps.{app_name}.infrastructure"
    assert not any(module.startswith(forbidden) for module in imports)


@pytest.mark.parametrize("app_name", BUSINESS_APPS)
def test_usecase_does_not_import_infrastructure(app_name: str):
    for path in _python_files_under(f"apps/{app_name}/usecase"):
        imports = _imports_in_file(path)
        forbidden = f"apps.{app_name}.infrastructure"
        assert not any(module.startswith(forbidden) for module in imports), path


@pytest.mark.parametrize("app_name", ("gonenkukumi", "receipt_comparison", "inventory_order_alert", "asset_inventory", "shipment_trend", "portal", "identity"))
def test_domain_does_not_import_django_or_outer_layers(app_name: str):
    forbidden_prefixes = (
        "django",
        f"apps.{app_name}.infrastructure",
        f"apps.{app_name}.usecase",
    )
    for path in _python_files_under(f"apps/{app_name}/domain"):
        imports = _imports_in_file(path)
        assert not any(module.startswith(forbidden_prefixes) for module in imports), path


def test_gonenkukumi_has_ports_and_usecases():
    assert (ROOT / "apps/gonenkukumi/usecase/usecase_search_page.py").is_file()
    assert (ROOT / "apps/gonenkukumi/usecase/usecase_export_excel.py").is_file()
    assert (ROOT / "apps/gonenkukumi/domain/ports.py").is_file()


def test_identity_has_usecase_modules():
    assert (ROOT / "apps/identity/usecase/usecase_login_page.py").is_file()
    assert (ROOT / "apps/identity/usecase/usecase_desknet_login.py").is_file()


def test_identity_usecase_only_has_usecase_files():
    app_dir = ROOT / "apps/identity/usecase"
    for path in app_dir.glob("*.py"):
        if path.name == "__init__.py":
            continue
        assert path.name.startswith("usecase_"), path


def test_receipt_comparison_usecase_modules_exist():
    usecase_dir = ROOT / "apps/receipt_comparison/usecase"
    assert (usecase_dir / "usecase_comparison_page.py").is_file()
    assert (usecase_dir / "usecase_compare.py").is_file()
    assert (usecase_dir / "usecase_register.py").is_file()
    assert (usecase_dir / "usecase_export_csv.py").is_file()
    assert (usecase_dir / "usecase_update_results.py").is_file()
    assert (usecase_dir / "usecase_settings.py").is_file()


def test_receipt_comparison_usecase_only_has_usecase_files():
    app_dir = ROOT / "apps/receipt_comparison/usecase"
    for path in app_dir.glob("*.py"):
        if path.name == "__init__.py":
            continue
        assert path.name.startswith("usecase_"), path


def test_receipt_comparison_has_domain_display_and_sort():
    assert (ROOT / "apps/receipt_comparison/domain/comparison_display.py").is_file()
    assert (ROOT / "apps/receipt_comparison/domain/comparison_sort.py").is_file()
    assert (ROOT / "apps/receipt_comparison/infrastructure/persistence/supplier_repository.py").is_file()
    assert (ROOT / "apps/receipt_comparison/infrastructure/persistence/model_registry.py").is_file()
    assert not (ROOT / "apps/receipt_comparison/type_registry.py").exists()


def test_gonenkukumi_usecase_only_has_usecase_files():
    app_dir = ROOT / "apps/gonenkukumi/usecase"
    for path in app_dir.glob("*.py"):
        if path.name == "__init__.py":
            continue
        assert path.name.startswith("usecase_"), path


def test_inventory_order_alert_usecase_modules_use_prefix():
    app_dir = ROOT / "apps/inventory_order_alert/usecase"
    usecase_files = [p.name for p in app_dir.glob("usecase_*.py")]
    assert "usecase_list_page.py" in usecase_files
    assert "usecase_import_stock.py" in usecase_files


def test_inventory_order_alert_usecase_only_has_usecase_files():
    app_dir = ROOT / "apps/inventory_order_alert/usecase"
    for path in app_dir.glob("*.py"):
        if path.name == "__init__.py":
            continue
        assert path.name.startswith("usecase_"), path


def test_inventory_order_alert_has_domain_ports_and_summary():
    assert (ROOT / "apps/inventory_order_alert/domain/ports.py").is_file()
    assert (ROOT / "apps/inventory_order_alert/domain/summary.py").is_file()
    assert (ROOT / "apps/inventory_order_alert/domain/list_rows.py").is_file()


def test_shipment_trend_usecase_only_has_usecase_files():
    app_dir = ROOT / "apps/shipment_trend/usecase"
    for path in app_dir.glob("*.py"):
        if path.name == "__init__.py":
            continue
        assert path.name.startswith("usecase_"), path


def test_shipment_trend_has_domain_ports_and_summary():
    assert (ROOT / "apps/shipment_trend/domain/ports.py").is_file()
    assert (ROOT / "apps/shipment_trend/domain/summary.py").is_file()
    assert (ROOT / "apps/shipment_trend/domain/trend_metrics.py").is_file()


def test_portal_usecase_has_usecase_modules():
    app_dir = ROOT / "apps/portal/usecase"
    assert (app_dir / "usecase_menu_access.py").is_file()
    assert (app_dir / "usecase_favorites.py").is_file()
    assert (app_dir / "usecase_bootstrap_local_dev.py").is_file()


def test_receipt_comparison_has_handlers_and_composition():
    assert not (ROOT / "apps/receipt_comparison/services").exists()
    assert not (ROOT / "apps/receipt_comparison/infrastructure/usecase_comparison.py").exists()
    assert (ROOT / "apps/receipt_comparison/composition.py").is_file()


def test_asset_inventory_usecase_only_has_usecase_files():
    app_dir = ROOT / "apps/asset_inventory/usecase"
    for path in app_dir.glob("*.py"):
        if path.name == "__init__.py":
            continue
        assert path.name.startswith("usecase_"), path


def test_asset_inventory_has_domain_ports():
    assert (ROOT / "apps/asset_inventory/domain/ports.py").is_file()
    assert (ROOT / "apps/asset_inventory/composition.py").is_file()
