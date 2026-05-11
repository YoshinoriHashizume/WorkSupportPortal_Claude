import {
  customerBannerOf,
  supplierBannerOf,
  type GonenBannerField,
} from "@/domains/gonenkukumi/block-banner-fields";
import type {
  CustomerShipBlock,
  SupplierBlock,
} from "@/domains/gonenkukumi/types";

function FieldSpan({ field }: { field: GonenBannerField }) {
  if (!field.label) {
    return <span className="text-sm font-semibold text-slate-900">{field.text}</span>;
  }
  return (
    <span>
      {field.label}：{" "}
      <span
        className={
          field.mono
            ? "font-mono font-medium text-slate-900"
            : "font-medium text-slate-900"
        }
      >
        {field.text}
      </span>
    </span>
  );
}

export function CustomerBannerHeader({ block }: { block: CustomerShipBlock }) {
  const banner = customerBannerOf(block);
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-normal text-slate-700">
      <FieldSpan field={banner.primary} />
      {banner.rest.map((f, i) => (
        <FieldSpan key={`${f.label ?? "_"}-${i}`} field={f} />
      ))}
    </div>
  );
}

export function SupplierBannerHeader({ block }: { block: SupplierBlock }) {
  const banner = supplierBannerOf(block);
  return (
    <div className="flex min-w-0 flex-col gap-2 text-xs font-normal text-slate-700">
      <div className="flex min-w-0 w-full items-baseline justify-between gap-3">
        <span className="min-w-0 truncate text-sm font-semibold text-slate-900">
          {banner.primary.text}
        </span>
        <span className="shrink-0 text-sm font-semibold tabular-nums text-slate-900">
          {banner.aside.text}
        </span>
      </div>
      <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1">
        {banner.rest.map((f, i) => (
          <FieldSpan key={`${f.label ?? "_"}-${i}`} field={f} />
        ))}
      </div>
    </div>
  );
}
