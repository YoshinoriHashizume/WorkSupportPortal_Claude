import "server-only";

/**
 * 5年9組 SQL で頻出する条件断片を集約。誤改修防止と意図の明示が目的。
 * バインドは `:asOf` / `:asOf2`（同値を 2 回渡す）、`:companyCd`。
 */

/**
 * M_CUST_ITEM の有効期間条件（VBA NAIJI_GET / CUST_NAYOSE と同じ式）。
 * `:asOf` / `:asOf2` は同値で渡す（Oracle は同一バインド名 2 回参照不可）。
 */
export const SQL_CUST_ITEM_EFF_RANGE = `
        M_CUST_ITEM.EFF_PHASE_IN_DATE <= TO_DATE(:asOf2, 'YYYY/MM/DD')
        AND (M_CUST_ITEM.EFF_PHASE_OUT_DATE IS NULL OR TO_DATE(:asOf, 'YYYY/MM/DD') <= M_CUST_ITEM.EFF_PHASE_OUT_DATE)`;
