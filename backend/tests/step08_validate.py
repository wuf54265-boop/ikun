"""Step 8 后端算法验证：RFM + 漏斗（手算/结构对照）。"""
import numpy as np
import pandas as pd

from app.core.stats_lib import funnel as lib_funnel
from app.core.stats_lib import rfm as lib_rfm

passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"[PASS] {name}")
    else:
        failed += 1
        print(f"[FAIL] {name}  ({detail})")


def test_rfm_basic():
    # 构造 12 个客户：最近/频繁/高额 → 冠军；久远/低频/低额 → 已流失；其余一般
    rows = []
    today = pd.Timestamp("2026-07-15")
    # 冠军客户：最近(0天)、高频、高额
    for i in range(3):
        rows.append(("C1", today, 1000.0))
        rows.append(("C1", today, 1000.0))
        rows.append(("C1", today, 1000.0))
    # 已流失：久远、低频、低额
    for i in range(3):
        rows.append(("C2", today - pd.Timedelta(days=170), 10.0))
    # 一般：中等
    for i in range(6):
        rows.append(("C3", today - pd.Timedelta(days=60), 200.0))

    df = pd.DataFrame(rows, columns=["cid", "dt", "amt"])
    out = lib_rfm.rfm_analysis(df, "cid", "dt", "amt", snapshot_date="2026-07-15")

    seg = {s["segment"]: s["count"] for s in out["segments"]}
    check("rfm 返回 6 个分群", len(out["segments"]) == 6)
    check("rfm 分群计数总和=3", sum(seg.values()) == 3, f"sum={sum(seg.values())}")
    check("rfm 占比总和≈1", abs(sum(s["share"] for s in out["segments"]) - 1.0) < 1e-3,
          f"sum={sum(s['share'] for s in out['segments'])}")
    # C1 应近冠军（R小F高M高），C2 应近已流失，C3 一般
    check("rfm 冠军客户存在", seg.get("冠军客户", 0) >= 1, f"{seg}")
    check("rfm 已流失存在", seg.get("已流失", 0) >= 1, f"{seg}")
    # matrix 每客户一条（top500），分数 1-5
    check("rfm matrix 行数=客户数(<=500)", len(out["matrix"]) == 3)
    for r in out["matrix"]:
        check(
            f"rfm 分数[{r['customer_id']}]∈1-5",
            all(1 <= r[k] <= 5 for k in ("score_r", "score_f", "score_m")),
            str(r),
        )
    # 建议数 = 出现的分群数
    present = sum(1 for s in out["segments"] if s["count"] > 0)
    check("rfm 建议数=出现分群数", len(out["suggestions"]) == present,
          f"sugg={len(out['suggestions'])} present={present}")


def test_rfm_top500():
    rng = np.random.default_rng(1)
    n = 800
    cids = [f"C{i:04d}" for i in range(1, n + 1)]
    df = pd.DataFrame({
        "cid": cids,
        "dt": pd.Timestamp("2026-07-15") - pd.to_timedelta(rng.integers(0, 180, n), unit="D"),
        "amt": rng.lognormal(4.0, 0.6, n).round(2),
    })
    out = lib_rfm.rfm_analysis(df, "cid", "dt", "amt")
    check("rfm 大数据 matrix 截断到 500", len(out["matrix"]) <= 500, f"len={len(out['matrix'])}")
    check("rfm 大数据分群总数=800", sum(s["count"] for s in out["segments"]) == n)


def test_funnel():
    df = pd.DataFrame({
        "浏览": [1, 1, 1, 1, 1, 0, 0],
        "加购": [1, 1, 1, 0, 0, 0, 0],
        "下单": [1, 1, 0, 0, 0, 0, 0],
    })
    out = lib_funnel.funnel_analysis(df, ["浏览", "加购", "下单"])
    steps = {s["step"]: s for s in out["steps"]}
    check("漏斗 浏览人数=5", steps["浏览"]["users"] == 5, str(steps))
    check("漏斗 加购人数=3", steps["加购"]["users"] == 3)
    check("漏斗 下单人数=2", steps["下单"]["users"] == 2)
    check("漏斗 浏览转化率=100", steps["浏览"]["conversion"] == 100.0)
    check("漏斗 下单转化率≈40", abs(steps["下单"]["conversion"] - 40.0) < 1e-6)
    # 最大流失 浏览(5)->加购(3) drop=2；加购(3)->下单(2) drop=1 → bottleneck=浏览→加购
    check("漏斗 bottleneck=浏览→加购", out["bottleneck"] == "浏览→加购", str(out["bottleneck"]))


def test_funnel_zero():
    df = pd.DataFrame({"a": [0, 0, 0], "b": [1, 1, 1]})
    out = lib_funnel.funnel_analysis(df, ["a", "b"])
    check("漏斗 全0列 users=0", out["steps"][0]["users"] == 0)
    check("漏斗 首步为0时转化率=0", out["steps"][1]["conversion"] == 0.0)
    check("漏斗 单步无 bottleneck", out["bottleneck"] is None, str(out["bottleneck"]))


def main():
    test_rfm_basic()
    test_rfm_top500()
    test_funnel()
    test_funnel_zero()
    print("\n" + "=" * 40)
    print(f"结果：{'全部通过' if failed == 0 else '存在失败'}  (PASS={passed}, FAIL={failed})")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
