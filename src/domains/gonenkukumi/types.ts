/** 日別数量（1 日＝インデックス 0）。VBA の列 F〜 と同様に日（1〜31）にマッピング */
export type DayQtySeries = (number | null)[];

/** 得意先ブロック（出荷側：6 データ行＋メタ） */
export type CustomerShipBlock = {
  custCode: string;
  custName: string;
  custItemCd: string;
  teban: number;
  anzen: number;
  /** 本日在庫（内作品番の T_ITEM_STOCK 合計） */
  zaiko: number;
  uncnfmByDay: DayQtySeries;
  /** 確定受注「前月残」列（VBA JUCHUZAN_GET） */
  confirmedOrderPrevBalance: number;
  confirmedOrderByDay: DayQtySeries;
  uniteOrderByDay: DayQtySeries;
  shipByDay: DayQtySeries;
  salesByDay: DayQtySeries;
};

/** 複数得意先品目があるときの集計行（VBA TOTAL_PUT） */
export type CustomerTotalsBlock = {
  uncnfmByDay: DayQtySeries;
  confirmedOrderByDay: DayQtySeries;
  uniteOrderByDay: DayQtySeries;
  shipByDay: DayQtySeries;
  salesByDay: DayQtySeries;
};

/** 仕入先（工程／入荷側：5 データ行） */
export type SupplierBlock = {
  vendCode: string;
  vendName: string;
  /** 入荷品番 + 階層表記 */
  itemCdWithLevel: string;
  /** BOM 階層（CONNECT BY の LEVEL） */
  kaiso: number;
  /** 手配区分（加工依頼・かんばん等。無ければ空） */
  arrangementTyp: string;
  /** 保管区（受入） */
  whCd: string;
  /** M_PS.CONS_TYP (0:非 1:有償支給 2:無償支給) */
  consTyp: number;
  topItemCd: string;
  teban: number;
  anzen: number;
  zaiko: number;
  monthlyStartByDay: DayQtySeries;
  demandByDay: DayQtySeries;
  /** 確定発注「前月以前残」列（VBA CHUZAN_GET） */
  confirmedPuchPrevBalance: number;
  confirmedPuchByDay: DayQtySeries;
  receiptByDay: DayQtySeries;
};

export type GonenKukumiOracleSuccess = {
  ok: true;
  internalItemCd: string;
  /** M_CAL.HOLIDAY_FLG が「0」以外の日（1〜31）。VBA CALEN_SET の休日着色に相当 */
  holidayDays: number[];
  customerBlocks: CustomerShipBlock[];
  /** 得意先が複数行のときのみ */
  customerTotals: CustomerTotalsBlock | null;
  supplierBlocks: SupplierBlock[];
};

export type GonenKukumiOracleFailure = {
  ok: false;
  code: "NAISAK_NOT_FOUND" | "ORACLE_ERROR" | "ORACLE_NOT_CONFIGURED";
  message: string;
};

export type GonenKukumiOracleResult = GonenKukumiOracleSuccess | GonenKukumiOracleFailure;
