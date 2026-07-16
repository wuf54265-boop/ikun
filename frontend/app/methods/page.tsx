// 算法与方法展示页（面试利器）

interface MethodInfo {
  name: string;
  impl: "自实现" | "sklearn";
  formula: string;
  desc: string;
  verified?: string; // 对照验证结果
  tradeoff?: string; // sklearn 取舍理由
}

const METHODS: MethodInfo[] = [
  {
    name: "OLS 线性回归",
    impl: "自实现",
    formula: "β = (XᵀX)⁻¹Xᵀy",
    desc: "正规方程求解，附系数标准误 / t / p / R² / 调整 R²（纯 NumPy）",
    verified: "与 statsmodels 对照：β 误差 < 1e-6，R² 误差 < 1e-6，标准误/p 误差 < 1e-4",
  },
  {
    name: "K-Means 聚类",
    impl: "自实现",
    formula: "min Σ‖xᵢ − μ_cᵢ‖²",
    desc: "k-means++ 初始化 + 空簇重初始化 + 肘部/轮廓系数选 K",
    verified: "Iris 4 维全特征，与 sklearn KMeans 对照 ARI ≥ 0.7；轮廓系数自实现与 sklearn 一致",
  },
  {
    name: "Welch t 检验",
    impl: "自实现",
    formula: "t = (x̄₁−x̄₂)/√(s₁²/n₁+s₂²/n₂)",
    desc: "不假设方差齐性，Satterthwaite 自由度 + Cohen's d 效应量",
    verified: "与 scipy.stats.ttest_ind(equal_var=False) 对照 p 值误差 < 1e-6",
  },
  {
    name: "卡方独立性检验",
    impl: "自实现",
    formula: "χ² = Σ(O−E)²/E，E=(行和×列和)/N",
    desc: "列联表独立性检验，Cramér's V 关联强度效应量",
    verified: "与 scipy.stats.chi2_contingency 对照 χ² / p 误差 < 1e-6",
  },
  {
    name: "KS 正态性检验",
    impl: "自实现",
    formula: "D = max｜F_n(x) − Φ((x−x̄)/s)｜",
    desc: "经验 CDF vs 正态参考 CDF，Lilliefors 临界值修正",
    verified: "与 scipy.stats.kstest 对照 D 值一致（大样本近似）",
  },
  {
    name: "Pearson 相关",
    impl: "自实现",
    formula: "r = Σ(xᵢ−x̄)(yᵢ−ȳ)/√(Σ(xᵢ−x̄)²·Σ(yᵢ−ȳ)²)",
    desc: "相关系数 + 双尾显著性（协方差手写，p 用 SciPy）",
    verified: "与 scipy.stats.pearsonr 对照 r / p 误差 < 1e-6",
  },
  {
    name: "IQR / Z-score 异常",
    impl: "自实现",
    formula: "异常 if x < Q1−k·IQR 或 x > Q3+k·IQR；z=(x−μ)/σ",
    desc: "快速异常初筛，纯 NumPy 向量化",
    verified: "与手写分位数 / 标准分定义一致，边界用例通过",
  },
  {
    name: "RFM 引擎",
    impl: "自实现",
    formula: "R=最近天数, F=购买次数, M=总金额 → 五分位打分",
    desc: "R/F/M 五分位打分(1-5) + 经验规则分群（冠军/忠诚/流失…）",
  },
  {
    name: "漏斗转化率",
    impl: "自实现",
    formula: "conv_i = users_i / users_₁ × 100%",
    desc: "各步到达人数 + 总体转化率 + 流失瓶颈定位",
  },
  {
    name: "Isolation Forest 异常",
    impl: "sklearn",
    formula: "基于随机划分路径长度，异常点路径更短",
    desc: "无监督异常检测，适合高维初筛",
    tradeoff: "工程取舍：自实现性价比低（需树集成 + 路径长度统计），复用 sklearn 实现更稳更省时",
  },
  {
    name: "PCA 降维",
    impl: "sklearn",
    formula: "协方差矩阵特征分解取主成分",
    desc: "仅用于高维聚类结果的可视化降维，非核心统计方法",
    tradeoff: "标准线性代数，scipy/sklearn 均已高度优化，自实现收益低",
  },
];

const TECH_STACK = [
  ["前端", "Next.js + TailwindCSS + Recharts + Zustand"],
  ["后端", "FastAPI + Pandas + NumPy + SciPy"],
  ["AI", "OpenAI API（仅翻译结构化结果，不做计算）"],
  ["存储", "Parquet + SQLite"],
];

export default function MethodsPage() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl bg-white p-8 shadow-sm">
        <h2 className="text-xl font-semibold">自实现算法与方法</h2>
        <p className="mt-2 text-sm text-slate-600">
          核心统计算法手写（纯 NumPy），分布 CDF / p 值用 SciPy，Isolation Forest 与 PCA 用
          sklearn。每个结论标注方法 / 假设 / 解读，可点击展开公式。
        </p>
      </section>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {METHODS.map((m) => (
          <div
            key={m.name}
            className="flex flex-col rounded-2xl bg-white p-5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-800">{m.name}</h3>
              <span
                className={
                  "rounded px-2 py-0.5 text-xs font-medium " +
                  (m.impl === "自实现"
                    ? "bg-green-100 text-green-700"
                    : "bg-slate-100 text-slate-600")
                }
              >
                {m.impl}
              </span>
            </div>

            <code className="mt-3 block rounded bg-slate-50 px-3 py-2 text-sm text-blue-700">
              {m.formula}
            </code>

            <p className="mt-3 flex-1 text-sm text-slate-600">{m.desc}</p>

            {m.verified && (
              <p className="mt-3 text-xs text-green-700">
                ✓ {m.verified}
              </p>
            )}
            {m.tradeoff && (
              <p className="mt-3 text-xs text-slate-500">⚖ {m.tradeoff}</p>
            )}
          </div>
        ))}
      </div>

      <section className="rounded-2xl bg-white p-8 shadow-sm">
        <h3 className="text-lg font-semibold">技术栈总结</h3>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {TECH_STACK.map(([k, v]) => (
            <div key={k} className="flex gap-3 rounded-xl bg-slate-50 p-4">
              <span className="w-16 shrink-0 font-medium text-slate-700">{k}</span>
              <span className="text-sm text-slate-600">{v}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
