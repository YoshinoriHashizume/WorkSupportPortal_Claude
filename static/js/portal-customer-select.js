(function () {
  function customerOptionLabel(customer) {
    const code = String(customer.custCode || "").trim();
    const name = String(customer.custName || "").trim();
    return name ? `${code} - ${name}` : code;
  }

  function fillSelect(select, customers) {
    const selected = String(select.dataset.selected || select.value || "").trim();
    const emptyLabel = select.dataset.emptyLabel ?? "選択してください";
    const allowEmpty = emptyLabel !== "";
    select.innerHTML = "";
    if (allowEmpty) {
      const emptyOption = document.createElement("option");
      emptyOption.value = "";
      emptyOption.textContent = emptyLabel;
      select.appendChild(emptyOption);
    }
    for (const customer of customers) {
      const option = document.createElement("option");
      option.value = customer.custCode;
      option.textContent = customerOptionLabel(customer);
      if (customer.custCode === selected) {
        option.selected = true;
      }
      select.appendChild(option);
    }
  }

  async function loadSelect(select) {
    const api = select.dataset.customersApi;
    if (!api) {
      return;
    }
    const response = await fetch(api);
    const payload = await response.json();
    if (!response.ok) {
      return;
    }
    fillSelect(select, payload.customers || []);
    select.dispatchEvent(new Event("portal-customer-select:loaded", { bubbles: true }));
  }

  window.portalCustomerSelectLabel = function portalCustomerSelectLabel(select, code) {
    const normalized = String(code || "").trim();
    const match = [...select.options].find((option) => option.value === normalized);
    return match?.textContent?.trim() || normalized;
  };

  window.initPortalCustomerSelects = async function initPortalCustomerSelects(root = document) {
    const selects = root.querySelectorAll("select.portal-customer-select[data-customers-api]");
    await Promise.all([...selects].map((select) => loadSelect(select)));
  };
})();
