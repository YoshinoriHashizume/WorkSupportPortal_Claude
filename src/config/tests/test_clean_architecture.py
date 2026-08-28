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


# --- 境界コンテキスト間の参照ルール（docs/strategic_design.md §3.1・§4） ---

#: 共有カーネル。どのコンテキストからも参照してよいモジュール接頭辞。
SHARED_KERNEL_PREFIXES = (
    # 一覧の絞り込み・並び替え・ページングの共通 VO
    "application.shared.domain",
    # 基幹 Oracle（MARI）参照専用 ACL
    "application.sales.domain.value_objects.errors",
    "application.sales.infrastructure.oracle",
    # 認可述語・お気に入り（interfaces 層からのみ利用する）
    "application.portal.interfaces.favorites",
    # desknet's NEO 参照 ACL
    "application.identity.domain.value_objects.errors",
    "application.identity.infrastructure.desknet",
)

#: 既知の未解消違反。解消するまでの一時的な許可であり、新規追加を禁止する。
#: 参照: docs/spec/ddd-review-remediation/tasks.md §2「今回実施しない指摘」
KNOWN_CONTEXT_LEAKS = {
    ("identity", "application.portal.domain.value_objects.constants"),
    ("identity", "application.portal.models"),
    ("sales", "application.gonenkukumi.infrastructure.oracle.client"),
    ("sales", "application.gonenkukumi.infrastructure.oracle.customers"),
}

CONTEXT_PACKAGES = BUSINESS_APPS + ("sales", "shared")


def _cross_context_imports(app_name: str) -> list[tuple[Path, str]]:
    """app_name の本番コードから他コンテキストへの import を列挙する。"""
    leaks: list[tuple[Path, str]] = []
    for path in _python_files_under(f"application/{app_name}"):
        parts = path.relative_to(ROOT).parts
        if "tests" in parts or "migrations" in parts:
            continue
        for module in _imports_in_file(path):
            segments = module.split(".")
            if len(segments) < 2 or segments[0] != "application":
                continue
            if segments[1] == app_name or segments[1] not in CONTEXT_PACKAGES:
                continue
            leaks.append((path, module))
    return leaks


@pytest.mark.parametrize("app_name", CONTEXT_PACKAGES)
def test_contexts_only_reference_the_shared_kernel(app_name: str):
    """境界コンテキストは共有カーネル以外の他コンテキストを参照しない。"""
    for path, module in _cross_context_imports(app_name):
        if any(module == prefix or module.startswith(prefix + ".") for prefix in SHARED_KERNEL_PREFIXES):
            continue
        # 合成ルート（interfaces/wiring.py）だけは他コンテキストの wiring を参照してよい
        if path.name == "wiring.py" and module.endswith(".interfaces.wiring"):
            continue
        if (app_name, module) in KNOWN_CONTEXT_LEAKS:
            continue
        raise AssertionError(
            f"{path.relative_to(ROOT)} が共有カーネル外の {module} を参照しています。"
            " 共有カーネルへ移すか、合成ルート経由に変更してください。"
        )


def test_known_context_leaks_are_not_stale():
    """解消済みの既知違反が KNOWN_CONTEXT_LEAKS に残り続けないようにする。"""
    actual = {(app, module) for app in CONTEXT_PACKAGES for _, module in _cross_context_imports(app)}
    stale = KNOWN_CONTEXT_LEAKS - actual
    assert not stale, f"解消済みの例外が残っています: {sorted(stale)}"


def test_shared_kernel_has_no_django_or_context_dependency():
    """共有カーネル（application/shared）は Django にも他コンテキストにも依存しない。"""
    for path in _python_files_under("application/shared"):
        if "tests" in path.relative_to(ROOT).parts:
            continue
        imports = _imports_in_file(path)
        assert not _has_django_import(imports), path
        assert not any(module.startswith("application.") for module in imports), path
