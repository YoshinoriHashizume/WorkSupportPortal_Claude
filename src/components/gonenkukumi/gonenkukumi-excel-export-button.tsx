"use client";

import { useState } from "react";
import type { GonenKukumiOracleSuccess } from "@/domains/gonenkukumi/types";
import {
  buildGonenKukumiExcelBuffer,
  buildGonenKukumiExcelBufferForMonths,
  defaultGonenExcelFilename,
  defaultGonenMultiMonthExcelFilename,
  type GonenExcelExportParams,
  type GonenMultiMonthExcelSlice,
} from "@/domains/gonenkukumi/excel-export";

export function GonenKukumiExcelExportButton({
  oracle,
  params,
  multiMonth,
}: {
  oracle: GonenKukumiOracleSuccess;
  params: GonenExcelExportParams;
  /** 指定時は表示中の全月を縦に連結して出力（日次は常に 31 列） */
  multiMonth?: { months: GonenMultiMonthExcelSlice[] };
}) {
  const [busy, setBusy] = useState(false);

  async function onClick() {
    if (busy) return;
    setBusy(true);
    try {
      const slices = multiMonth?.months?.filter((m) => m.oracle);
      const buf =
        slices && slices.length > 0
          ? await buildGonenKukumiExcelBufferForMonths(slices, params)
          : await buildGonenKukumiExcelBuffer(oracle, params);
      const name =
        slices && slices.length > 0
          ? defaultGonenMultiMonthExcelFilename(
              params,
              slices.map((s) => s.yearMonth),
            )
          : defaultGonenExcelFilename(params);
      const blob = new Blob([buf], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      window.alert("Excel の出力に失敗しました。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={() => void onClick()}
      disabled={busy}
      className="rounded-md border border-emerald-600 bg-white px-3 py-1.5 text-sm font-medium text-emerald-800 shadow-sm hover:bg-emerald-50 disabled:opacity-50"
    >
      {busy ? "出力中…" : "Excelで出力"}
    </button>
  );
}
