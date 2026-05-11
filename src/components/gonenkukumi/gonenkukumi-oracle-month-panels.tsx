"use client";

import type { CSSProperties } from "react";
import type {
  CustomerShipBlock,
  DayQtySeries,
  GonenKukumiOracleSuccess,
  SupplierBlock,
} from "@/domains/gonenkukumi/types";
import { gonenQtyCellJa } from "@/domains/gonenkukumi/gonen-display-format";
import {
  daysInMonthYm,
  GONEN_FIXED_GRID_BORDER_HEX,
  GONEN_PAD_DAY_HEX,
  GONEN_REPORT_GRID_DAYS,
  ymdForDay,
} from "@/domains/gonenkukumi/report-grid";
import { GonenkukumiCellFit } from "@/components/gonenkukumi/gonenkukumi-cell-fit";
import { kaisoColor } from "@/domains/gonenkukumi/kaiso-color";
import type { GonenPanelSegment } from "@/domains/gonenkukumi/panel-segments";
import {
  findCustomerBlock,
  findSupplierBlock,
} from "@/domains/gonenkukumi/block-finders";
import {
  gonenSegmentKaisoIndex,
  gonenSupplierBlockKaisoIndex,
} from "@/domains/gonenkukumi/segment-theme";
import {
  resolveCustomerRows,
  resolveSupplierRows,
} from "@/domains/gonenkukumi/block-rows";
import {
  CustomerBannerHeader,
  SupplierBannerHeader,
} from "@/components/gonenkukumi/block-banner-header";

export type { GonenPanelSegment };

export type GonenKukumiResultPanelParams = {
  custCode: string;
  custItem: string;
  optionChange: string;
  yearMonth: string;
  asOfDate: string;
};

function weekendBgClass(ym: string, day: number): string {
  const d = ymdForDay(ym, day);
  if (!d) return "";
  const w = d.getDay(); // 0:Sun ... 6:Sat
  if (w === 0) return "bg-rose-50";
  if (w === 6) return "bg-sky-50";
  return "";
}

/** M_CAL 休日は土日より優先して着色（VBA の休日セルに相当） */
function dayColumnBgClass(
  ym: string,
  day: number,
  holidays: ReadonlySet<number>,
  holidayBgClass: string,
): string {
  if (holidays.has(day)) return holidayBgClass;
  return weekendBgClass(ym, day);
}

const padDaySolidStyle: CSSProperties = {
  backgroundColor: GONEN_PAD_DAY_HEX,
  borderColor: GONEN_PAD_DAY_HEX,
  borderStyle: "solid",
  borderWidth: 1,
};

type SectionTheme = ReturnType<typeof kaisoColor>;

const reportTableClassName = "min-w-full w-full table-fixed border-collapse text-sm";

const COL_LEAD_PCT = { label: 5, rowSum: 5, prev: 5 } as const;

function CommonColGroup() {
  const maxDay = GONEN_REPORT_GRID_DAYS;
  const dayShare =
    100 - COL_LEAD_PCT.label - COL_LEAD_PCT.rowSum - COL_LEAD_PCT.prev;
  const dayColPct = maxDay > 0 ? dayShare / maxDay : 0;
  return (
    <colgroup>
      <col style={{ width: `${COL_LEAD_PCT.label}%` }} />
      <col style={{ width: `${COL_LEAD_PCT.rowSum}%` }} />
      <col style={{ width: `${COL_LEAD_PCT.prev}%` }} />
      {Array.from({ length: maxDay }, (_, i) => (
        <col key={i} style={{ width: `${dayColPct}%` }} />
      ))}
    </colgroup>
  );
}

function DayHeaderCells({
  activeDays,
  theme,
}: {
  activeDays: number;
  theme: SectionTheme;
}) {
  return (
    <>
      {Array.from({ length: GONEN_REPORT_GRID_DAYS }, (_, i) => {
        const day = i + 1;
        const isPad = day > activeDays;
        return (
          <th
            key={i}
            style={
              isPad
                ? padDaySolidStyle
                : { backgroundColor: theme.cssBg, borderColor: theme.cssBorder }
            }
            className={`px-0.5 py-1 text-right whitespace-nowrap tabular-nums ${isPad ? "" : "border"}`}
          >
            {isPad ? null : (
              <GonenkukumiCellFit align="right" className="tabular-nums">
                {day}日
              </GonenkukumiCellFit>
            )}
          </th>
        );
      })}
    </>
  );
}

function DayCells({
  series,
  activeDays,
  yearMonth,
  holidaySet,
  theme,
  className,
}: {
  series: DayQtySeries;
  activeDays: number;
  yearMonth: string;
  holidaySet: ReadonlySet<number>;
  theme: SectionTheme;
  className?: string;
}) {
  return (
    <>
      {Array.from({ length: GONEN_REPORT_GRID_DAYS }, (_, i) => {
        const day = i + 1;
        const isPad = day > activeDays;
        if (isPad) {
          return (
            <td key={i} style={padDaySolidStyle} className="px-0.5 py-1" />
          );
        }
        return (
          <td
            key={i}
            style={{
              ...(holidaySet.has(day) ? { backgroundColor: theme.cssBg } : {}),
              borderColor: GONEN_FIXED_GRID_BORDER_HEX,
            }}
            className={`border border-slate-200 px-0.5 py-1 text-right tabular-nums whitespace-nowrap ${dayColumnBgClass(
              yearMonth,
              day,
              holidaySet,
              "",
            )} ${className ?? ""}`}
          >
            <GonenkukumiCellFit align="right" className="tabular-nums">
              {gonenQtyCellJa(series[i])}
            </GonenkukumiCellFit>
          </td>
        );
      })}
    </>
  );
}

function BlockTableHeader({ theme }: { theme: SectionTheme }) {
  return (
    <>
      <th style={{ backgroundColor: theme.cssBg, borderColor: theme.cssBorder }} className="border px-2 py-1 whitespace-nowrap">
        <GonenkukumiCellFit>区分</GonenkukumiCellFit>
      </th>
      <th style={{ backgroundColor: theme.cssBg, borderColor: theme.cssBorder }} className="border px-2 py-1 text-right whitespace-nowrap">
        <GonenkukumiCellFit align="right">行計</GonenkukumiCellFit>
      </th>
      <th style={{ backgroundColor: theme.cssBg, borderColor: theme.cssBorder }} className="border px-2 py-1 text-right whitespace-nowrap">
        <GonenkukumiCellFit align="right">前月残／在庫</GonenkukumiCellFit>
      </th>
    </>
  );
}

type BlockTableRowDescriptor = {
  label: string;
  prev: number | null;
  rowSum: number | null;
  series: DayQtySeries;
  webClass: string;
};

function BlockTableBodyRow({
  row,
  activeDays,
  yearMonth,
  holidaySet,
  theme,
}: {
  row: BlockTableRowDescriptor;
  activeDays: number;
  yearMonth: string;
  holidaySet: ReadonlySet<number>;
  theme: SectionTheme;
}) {
  return (
    <tr>
      <td
        style={{ backgroundColor: theme.cssBg, borderColor: theme.cssBorder }}
        className="border px-2 py-1 font-medium text-slate-800 whitespace-nowrap"
      >
        <GonenkukumiCellFit className="font-medium text-slate-800">{row.label}</GonenkukumiCellFit>
      </td>
      <td
        style={{ borderColor: GONEN_FIXED_GRID_BORDER_HEX }}
        className={`border px-2 py-1 text-right tabular-nums font-medium whitespace-nowrap ${row.webClass}`}
      >
        <GonenkukumiCellFit align="right" className="tabular-nums font-medium">
          {gonenQtyCellJa(row.rowSum)}
        </GonenkukumiCellFit>
      </td>
      <td
        style={{ borderColor: GONEN_FIXED_GRID_BORDER_HEX }}
        className={`border px-2 py-1 text-right tabular-nums whitespace-nowrap ${row.webClass}`}
      >
        <GonenkukumiCellFit align="right" className="tabular-nums">
          {gonenQtyCellJa(row.prev)}
        </GonenkukumiCellFit>
      </td>
      <DayCells
        series={row.series}
        activeDays={activeDays}
        yearMonth={yearMonth}
        holidaySet={holidaySet}
        theme={theme}
        className={row.webClass}
      />
    </tr>
  );
}

function CustomerBlockTable({
  block,
  activeDays,
  yearMonth,
  holidaySet,
  theme,
}: {
  block: CustomerShipBlock;
  activeDays: number;
  yearMonth: string;
  holidaySet: ReadonlySet<number>;
  theme: SectionTheme;
}) {
  const rows = resolveCustomerRows(block, activeDays);

  return (
    <div style={{ outline: `2px solid ${theme.cssOuterBorder}`, outlineOffset: "-1px" }}>
      <table className={reportTableClassName}>
        <CommonColGroup />
        <thead>
          <tr className="text-left text-slate-800">
            <BlockTableHeader theme={theme} />
            <DayHeaderCells activeDays={activeDays} theme={theme} />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <BlockTableBodyRow
              key={r.spec.label}
              row={{
                label: r.spec.label,
                prev: r.prev,
                rowSum: r.rowSum,
                series: r.series,
                webClass: r.spec.webClass,
              }}
              activeDays={activeDays}
              yearMonth={yearMonth}
              holidaySet={holidaySet}
              theme={theme}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SupplierBlockTable({
  block,
  activeDays,
  yearMonth,
  holidaySet,
  theme,
}: {
  block: SupplierBlock;
  activeDays: number;
  yearMonth: string;
  holidaySet: ReadonlySet<number>;
  theme: SectionTheme;
}) {
  const rows = resolveSupplierRows(block, activeDays);

  return (
    <div style={{ outline: `2px solid ${theme.cssOuterBorder}`, outlineOffset: "-1px" }}>
      <table className={reportTableClassName}>
        <CommonColGroup />
        <thead>
          <tr className="text-left text-slate-800">
            <BlockTableHeader theme={theme} />
            <DayHeaderCells activeDays={activeDays} theme={theme} />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <BlockTableBodyRow
              key={r.spec.label}
              row={{
                label: r.spec.label,
                prev: r.prev,
                rowSum: r.rowSum,
                series: r.series,
                webClass: r.spec.webClass,
              }}
              activeDays={activeDays}
              yearMonth={yearMonth}
              holidaySet={holidaySet}
              theme={theme}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** 複数月ビューでは filter で 1 ブロックを指定。省略時は該当種別の全ブロック（表のみのコンパクト表示）。 */

/** 1 か月分の Oracle 成功結果（得意先／仕入先ブロック）。segment 指定時は該当ブロックのみ（Web では TOTAL は表示しない） */
export function GonenKukumiOracleMonthPanels({
  oracle,
  params,
  segment,
}: {
  oracle: GonenKukumiOracleSuccess;
  params: GonenKukumiResultPanelParams;
  segment?: GonenPanelSegment;
}) {
  const activeDays = daysInMonthYm(params.yearMonth);
  const holidaySet = new Set(oracle.holidayDays);

  if (segment?.kind === "cust") {
    if (segment.filter) {
      const block = findCustomerBlock(oracle.customerBlocks, segment.filter);
      if (!block) {
        return (
          <p className="px-2 py-4 text-sm text-slate-500">この月は該当の得意先行がありません。</p>
        );
      }
      const theme = kaisoColor(gonenSegmentKaisoIndex(segment, oracle));
      return (
        <div className="overflow-x-auto">
          <CustomerBlockTable
            block={block}
            activeDays={activeDays}
            yearMonth={params.yearMonth}
            holidaySet={holidaySet}
            theme={theme}
          />
        </div>
      );
    }
    return (
      <div className="space-y-6">
        {oracle.customerBlocks.map((block, bi) => {
          const theme = kaisoColor(1);
          return (
            <div key={`${block.custCode}-${bi}`} className="overflow-x-auto">
              <CustomerBlockTable
                block={block}
                activeDays={activeDays}
                yearMonth={params.yearMonth}
                holidaySet={holidaySet}
                theme={theme}
              />
            </div>
          );
        })}
      </div>
    );
  }

  if (segment?.kind === "sup") {
    if (segment.filter) {
      const block = findSupplierBlock(oracle.supplierBlocks, segment.filter);
      if (!block) {
        return (
          <p className="px-2 py-4 text-sm text-slate-500">この月は該当の仕入先行がありません。</p>
        );
      }
      const theme = kaisoColor(gonenSegmentKaisoIndex(segment, oracle));
      return (
        <div className="overflow-x-auto">
          <SupplierBlockTable
            block={block}
            activeDays={activeDays}
            yearMonth={params.yearMonth}
            holidaySet={holidaySet}
            theme={theme}
          />
        </div>
      );
    }
    return (
      <div className="space-y-6">
        {oracle.supplierBlocks.map((block, si) => {
          const theme = kaisoColor(gonenSupplierBlockKaisoIndex(block));
          return (
            <div key={`${block.vendCode}-${block.itemCdWithLevel}-${si}`} className="overflow-x-auto">
              <SupplierBlockTable
                block={block}
                activeDays={activeDays}
                yearMonth={params.yearMonth}
                holidaySet={holidaySet}
                theme={theme}
              />
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {oracle.customerBlocks.map((block, bi) => {
        const theme = kaisoColor(1);
        return (
          <section
            key={`${block.custCode}-${bi}`}
            style={{ borderColor: theme.cssOuterBorder }}
            className="overflow-x-auto rounded-lg border-2 bg-white shadow-sm"
          >
            <h2
              style={{ backgroundColor: theme.cssBg, borderColor: theme.cssBorder }}
              className="border-b px-4 py-2"
            >
              <CustomerBannerHeader block={block} />
            </h2>
            <div className="p-2">
              <CustomerBlockTable
                block={block}
                activeDays={activeDays}
                yearMonth={params.yearMonth}
                holidaySet={holidaySet}
                theme={theme}
              />
            </div>
          </section>
        );
      })}

      {oracle.supplierBlocks.map((block, si) => {
        const theme = kaisoColor(gonenSupplierBlockKaisoIndex(block));
        return (
          <section
            key={`${block.vendCode}-${block.itemCdWithLevel}-${si}`}
            style={{ borderColor: theme.cssOuterBorder }}
            className="overflow-x-auto rounded-lg border-2 bg-white shadow-sm"
          >
            <h2
              style={{
                backgroundColor: theme.cssBg,
                borderColor: theme.cssBorder,
              }}
              className="border-b px-4 py-2"
            >
              <SupplierBannerHeader block={block} />
            </h2>
            <div className="p-2">
              <SupplierBlockTable
                block={block}
                activeDays={activeDays}
                yearMonth={params.yearMonth}
                holidaySet={holidaySet}
                theme={theme}
              />
            </div>
          </section>
        );
      })}
    </div>
  );
}
