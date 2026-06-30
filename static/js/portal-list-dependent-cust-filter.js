(function () {
  function buildCustChrgCustIndex(rows) {
    const index = new Map();
    for (const row of rows) {
      const chrgCode = String(row.cust_chrg_psn_cd || "").trim();
      const custCode = String(row.cust_code || "").trim();
      const custName = String(row.cust_name || "").trim();
      if (!chrgCode || !custCode) {
        continue;
      }
      if (!index.has(chrgCode)) {
        index.set(chrgCode, new Map());
      }
      const bucket = index.get(chrgCode);
      if (custName) {
        bucket.set(custCode, custName);
      } else if (!bucket.has(custCode)) {
        bucket.set(custCode, "");
      }
    }
    return index;
  }

  function custOptionsForChrg(allCustOptions, index, chrgPsnCd) {
    const chrgCode = String(chrgPsnCd || "").trim();
    if (!chrgCode) {
      return allCustOptions;
    }
    const allowed = index.get(chrgCode);
    if (!allowed) {
      return [];
    }
    return allCustOptions.filter((option) => allowed.has(option.value));
  }

  function sanitizeCustCode(custCode, visibleOptions) {
    const code = String(custCode || "").trim();
    if (!code) {
      return "";
    }
    const valid = new Set(visibleOptions.map((option) => option.value));
    return valid.has(code) ? code : "";
  }

  function renderCustCodeSelect(select, allCustOptions, index, chrgPsnCd, selectedValue) {
    const visibleOptions = custOptionsForChrg(allCustOptions, index, chrgPsnCd);
    const sanitized = sanitizeCustCode(selectedValue, visibleOptions);
    if (!select) {
      return sanitized;
    }
    select.replaceChildren();
    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = "すべて";
    select.appendChild(emptyOption);
    visibleOptions.forEach((option) => {
      const element = document.createElement("option");
      element.value = option.value;
      element.textContent = option.label;
      if (option.value === sanitized) {
        element.selected = true;
      }
      select.appendChild(element);
    });
    select.value = sanitized;
    return sanitized;
  }

  window.PortalListDependentCustFilter = {
    buildCustChrgCustIndex,
    custOptionsForChrg,
    sanitizeCustCode,
    renderCustCodeSelect,
  };
})();
