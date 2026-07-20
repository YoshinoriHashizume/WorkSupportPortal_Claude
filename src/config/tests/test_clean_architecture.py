from __future__ import annotations

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]  # = src/

BUSINESS_APPS = (
    "gonenkukumi",
    "receipt_comparison",
    "inventory_order_alert",
    "asset_inventory",
    "shipment_trend",
    "portal",
    "identity",
)

REQUIRED_DOMAIN_SUBDIRS = ("entities", "value_objects", "repositories")
REQUIRED_INTERFACE_FILES = ("views.py", "urls.py", "wiring.py")


def _python_files_under(relative: str) -> list[Path]:
    base = ROOT / relative
    if not base.exists():
        return []
    return sorted(path for path in base.rglob("*.py") if path.name != "__init__.py")


def _imports_in_file(path: Path, *, skip_type_checking: bool = True) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    skipped: set[int] = set()
    if skip_type_checking:
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                for child in ast.walk(node):
                    skipped.add(id(child))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if id(node) in skipped:
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _has_django_import(imports: set[str]) -> bool:
    return any(module == "django" or module.startswith("django.") for module in imports)


@pytest.mark.parametrize("app_name", BUSINESS_APPS)
def test_app_has_clean_architecture_layers(app_name: str):
    app_root = ROOT / "application" / app_name
    assert (app_root / "domain").is_dir(), f"{app_name} missing domain/"
    assert (app_root / "use_cases").is_dir(), f"{app_name} missing use_cases/"
    assert (app_root / "infrastructure").is_dir(), f"{app_name} missing infrastructure/"
    interfaces = app_root / "interfaces"
    assert interfaces.is_dir(), f"{app_name} missing interfaces/"
    for name in REQUIRED_INTERFACE_FILES:
        assert (interfaces / name).is_file(), f"{app_name} missing interfaces/{name}"
    assert not (app_root / "composition.py").exists(), f"{app_name} must not have composition.py"
    assert not (interfaces / "composition.py").exists(), f"{app_name} must not have interfaces/composition.py"


@pytest.mark.parametrize("app_name", BUSINESS_APPS)
def test_domain_has_entities_value_objects_repositories(app_name: str):
    domain = ROOT / "application" / app_name / "domain"
    for subdir in REQUIRED_DOMAIN_SUBDIRS:
        assert (domain / subdir).is_dir(), f"{app_name} missing domain/{subdir}/"
    assert (domain / "repositories" / "ports.py").is_file(), (
        f"{app_name} missing domain/repositories/ports.py"
    )


@pytest.mark.parametrize("app_name", BUSINESS_APPS)
def test_use_cases_directory_has_python_modules(app_name: str):
    use_cases_dir = ROOT / "application" / app_name / "use_cases"
    modules = [p for p in use_cases_dir.glob("*.py") if p.name != "__init__.py"]
    assert modules, f"{app_name} use_cases/ must contain at least one module"


@pytest.mark.parametrize("app_name", BUSINESS_APPS)
def test_views_do_not_import_use_cases_directly(app_name: str):
    """views は wiring 経由でユースケースを得る（直接 use_cases を import しない）。"""
    views_path = ROOT / "application" / app_name / "interfaces" / "views.py"
    imports = _imports_in_file(views_path)
    forbidden = f"application.{app_name}.use_cases"
    assert not any(module.startswith(forbidden) for module in imports), views_path


@pytest.mark.parametrize("app_name", BUSINESS_APPS)
def test_views_do_not_import_own_infrastructure(app_name: str):
    """views は infrastructure を直 import しない（wiring 経由）。"""
    views_path = ROOT / "application" / app_name / "interfaces" / "views.py"
    imports = _imports_in_file(views_path)
    forbidden = f"application.{app_name}.infrastructure"
    assert not any(module == forbidden or module.startswith(forbidden + ".") for module in imports), views_path


@pytest.mark.parametrize("app_name", BUSINESS_APPS)
def test_use_cases_do_not_import_django_or_own_infrastructure(app_name: str):
    forbidden_infra = f"application.{app_name}.infrastructure"
    forbidden_models = f"application.{app_name}.models"
    for path in _python_files_under(f"application/{app_name}/use_cases"):
        imports = _imports_in_file(path)
        assert not _has_django_import(imports), path
        assert not any(module.startswith(forbidden_infra) for module in imports), path
        assert not any(module == forbidden_models or module.startswith(forbidden_models + ".") for module in imports), path


@pytest.mark.parametrize("app_name", BUSINESS_APPS)
def test_views_do_not_import_own_models(app_name: str):
    """views は ORM モデルを直 import しない（wiring / domain 経由）。"""
    views_path = ROOT / "application" / app_name / "interfaces" / "views.py"
    imports = _imports_in_file(views_path)
    forbidden = f"application.{app_name}.models"
    assert not any(module == forbidden or module.startswith(forbidden + ".") for module in imports), views_path


@pytest.mark.parametrize("app_name", BUSINESS_APPS)
def test_domain_does_not_import_django_or_outer_layers(app_name: str):
    forbidden_prefixes = (
        "django",
        f"application.{app_name}.infrastructure",
        f"application.{app_name}.use_cases",
        f"application.{app_name}.interfaces",
        f"application.{app_name}.models",
    )
    for path in _python_files_under(f"application/{app_name}/domain"):
        imports = _imports_in_file(path)
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for prefix in forbidden_prefixes
            for module in imports
        ), path


def test_receipt_comparison_has_no_services_layer():
    assert not (ROOT / "application" / "receipt_comparison" / "services").exists()


def test_wiring_is_manual_di_not_container():
    """interfaces/wiring.py は手動組み立て。DI コンテナライブラリを使わない。"""
    container_markers = ("dependency_injector", "punq", "injector", "lagom")
    for app_name in BUSINESS_APPS:
        wiring = ROOT / "application" / app_name / "interfaces" / "wiring.py"
        text = wiring.read_text(encoding="utf-8-sig")
        for marker in container_markers:
            assert marker not in text, f"{app_name} wiring uses container lib: {marker}"
