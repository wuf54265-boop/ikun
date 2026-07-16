"""Step 8 端到端冒烟：demo 端点 + RFM + 漏斗（TestClient）。"""
import io

from fastapi.testclient import TestClient

from app.main import app

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


def test_main():
    # 用 with 进入上下文触发 lifespan（建表 init_db）；
    # 否则 datasets 表不存在，/datasets/demo 会报 no such table。
    with TestClient(app) as client:
        # 1) Demo 端点
        r = client.post("/api/v1/datasets/demo")
        check("demo 端点 200", r.status_code == 200, r.text[:200])
        if r.status_code == 200:
            body = r.json()
            did = body["data"]["dataset_id"]
            check("demo 返回 dataset_id", bool(did), str(body)[:120])
            check("demo 行数≈500", body["data"]["rows"] >= 400, str(body["data"]["rows"]))
            check("demo 元信息 method=demo_dataset",
                  body["meta"]["method"] == "demo_dataset", str(body["meta"]))
            check("demo explanation 为对象（非裸串）",
                  isinstance(body.get("explanation"), dict), str(body.get("explanation")))

            # 2) RFM
            rfm_body = {
                "dataset_id": did,
                "customer_id": "customer_id",
                "date": "order_date",
                "amount": "amount",
            }
            r2 = client.post("/api/v1/templates/rfm", json=rfm_body)
            check("RFM 端点 200", r2.status_code == 200, r2.text[:200])
            if r2.status_code == 200:
                j2 = r2.json()
                segs = {s["segment"]: s["count"] for s in j2["data"]["segments"]}
                total = sum(segs.values())
                check("RFM 分群覆盖全部客户(>0)", total > 0, str(segs))
                check("RFM 含多类人群", len([c for c in segs.values() if c > 0]) >= 2, str(segs))
                check("RFM explanation 含方法", "method" in j2["explanation"], str(j2["explanation"]))
                check("RFM meta.method=rfm", j2["meta"]["method"] == "rfm", str(j2["meta"]))

            # 3) 漏斗（用 demo 的 4 列作为步骤示例）
            funnel_body = {
                "dataset_id": did,
                "steps": ["quantity", "amount", "is_member", "channel"],
            }
            r3 = client.post("/api/v1/templates/funnel", json=funnel_body)
            check("漏斗 端点 200", r3.status_code == 200, r3.text[:200])
            if r3.status_code == 200:
                j3 = r3.json()
                steps = j3["data"]["steps"]
                check("漏斗 步骤数=4", len(steps) == 4, str(steps))
                check("漏斗 第一步转化率=100", steps[0]["conversion"] == 100.0, str(steps))
                # quantity 列全非0（1..5），转化率应 100
                check("漏斗 quantity 步 100%", steps[0]["conversion"] == 100.0, str(steps))
                check("漏斗 bottleneck 为字符串或None",
                      j3["data"]["bottleneck"] is None or isinstance(j3["data"]["bottleneck"], str))
                check("漏斗 explanation 含方法", "method" in j3["explanation"], str(j3["explanation"]))

        print("\n" + "=" * 40)
        print(f"结果：{'全部通过' if failed == 0 else '存在失败'}  (PASS={passed}, FAIL={failed})")
    # 作为 pytest 用例：任何子检查失败都应让用例失败（不再用 SystemExit）
    assert failed == 0, f"{failed} 项端点检查失败 (PASS={passed})"


if __name__ == "__main__":
    test_main()
