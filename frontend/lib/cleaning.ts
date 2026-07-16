// 清洗页共享逻辑：由 profile 派生缺失信息 + 推荐策略（口径与后端 analyze_missing 一致）
import type { FieldProfile } from "./types";

export interface MissingColumnInfo {
  column: string;
  dtype: string;
  missingCount: number;
  missingRate: number;
  isConstant: boolean;
  recommended: "keep" | "drop" | "median" | "mode" | "review";
}

// 阈值与后端 services.cleaning.analyze_missing 保持一致
const DROP_ROWS_RATE = 0.05;
const HIGH_MISSING_RATE = 0.3;

export function deriveMissingInfo(
  fields: FieldProfile[],
  rows: number
): MissingColumnInfo[] {
  return fields.map((f) => {
    const missingRate = f.missing_rate ?? 0;
    const missingCount = Math.round((missingRate / 100) * rows);
    // 阈值与后端 services.cleaning.analyze_missing 一致（后端用比率 0~1）
    const rate = missingRate / 100;
    let recommended: MissingColumnInfo["recommended"];
    if (missingRate === 0) recommended = "keep";
    else if (rate < DROP_ROWS_RATE) recommended = "drop";
    else if (rate <= HIGH_MISSING_RATE)
      recommended = f.inferred_type === "numeric" ? "median" : "mode";
    else recommended = "review";
    return {
      column: f.name,
      dtype: f.dtype,
      missingCount,
      missingRate: missingRate / 100,
      isConstant: f.is_constant,
      recommended,
    };
  });
}
