import { z } from "zod";

/** API の対象日付クエリ等で共有（`yyyy/mm/dd`） */
export const GONEN_AS_OF_DATE_REGEX = /^\d{4}\/\d{2}\/\d{2}$/;

/** 5年9組 検索条件（仕様書 IN-01〜IN-05） */
export const gonenKukumiSearchSchema = z.object({
  custCode: z.string().min(1, "得意先コードを入力してください"),
  custItem: z.string().min(1, "得意先品目を入力してください"),
  optionChange: z.string().optional().default("*"),
  yearMonth: z.string().regex(/^\d{4}\/\d{2}$/, "検索年月は yyyy/mm 形式で入力してください"),
  asOfDate: z.string().regex(GONEN_AS_OF_DATE_REGEX, "対象日付は yyyy/mm/dd 形式で入力してください"),
});

export type GonenKukumiSearchInput = z.infer<typeof gonenKukumiSearchSchema>;
