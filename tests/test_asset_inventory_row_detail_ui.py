from pathlib import Path

from django.conf import settings


def test_TC_AIV_DOM_070_compare_table_column_layout():
    css_path = Path(settings.BASE_DIR) / "static" / "css" / "app.css"
    source = css_path.read_text(encoding="utf-8")

    assert "col.aiv-row-detail-compare-col-label" in source
    assert "width: 24%;" in source
    assert "width: 38%;" in source
    assert "scrollbar-gutter: stable" in source
    assert ".aiv-row-detail-compare-wrap" in source and "min-width: 0" in source


def test_TC_AIV_DOM_071_row_detail_dialog_initializes_before_display():
    js_path = Path(settings.BASE_DIR) / "static" / "js" / "asset-inventory-list.js"
    source = js_path.read_text(encoding="utf-8")

    assert "function resetDetailDialog()" in source
    assert "function clearPhoto(image, emptyLabel)" in source
    assert "function showLoadedPhoto(image, emptyLabel)" in source
    assert 'image.loading = "eager"' in source
    assert "image.complete && image.naturalWidth > 0" in source

    open_detail_index = source.index("function openDetail(rowKey)")
    reset_index = source.index("resetDetailDialog();", open_detail_index)
    show_modal_index = source.index("dialog.showModal();", open_detail_index)
    set_photo_index = source.index("setPhoto(assetImage", open_detail_index)
    assert reset_index < show_modal_index
    assert show_modal_index < set_photo_index


def test_TC_AIV_DOM_072_photo_zoom_dialog():
    js_path = Path(settings.BASE_DIR) / "static" / "js" / "asset-inventory-list.js"
    source = js_path.read_text(encoding="utf-8")

    assert "function initPhotoZoomDialog(detailDialog)" in source
    assert 'img.is-clickable' in source
    assert "aiv-photo-zoom-dialog" in source
    assert "zoomDialog.showModal()" in source

    template_path = Path(settings.BASE_DIR) / "templates" / "asset_inventory" / "list.html"
    template = template_path.read_text(encoding="utf-8")
    assert 'id="aiv-photo-zoom-dialog"' in template
    assert "aiv-photo-zoom-image" in template
