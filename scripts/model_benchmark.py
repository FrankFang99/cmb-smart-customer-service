"""
模型选型 A/B Benchmark (M1/M2/M3/M4)
=====================================
- M1/M2/M3: 调用 train_bert_intent.py --model X 后台跑
- M4: rule+keyword 基线 (0 训练, 0ms), 跑 holdout 看上限
- 最终汇总对比表

业界做法: 统一 holdout 评测, 按 (acc, latency, model_size) 选 Pareto
"""
import os
import sys
import json
import time
import argparse
import subprocess

PROJECT_ROOT = r"D:\Learning\AI\面试\AI智能客服"
sys.path.insert(0, PROJECT_ROOT)
os.environ["PYTHONIOENCODING"] = "utf-8"

# 4 个模型
MODELS = {
    "M1": {
        "name": "bert-tiny-chinese",
        "n_freeze": 0,  # tiny 只有 2 层, 不冻
        "epochs": 5,
        "batch_size": 64,  # tiny 4M, 大 batch
        "lr": 1e-4,
        "max_len": 16,
        "estimated_time_min": 5,
    },
    "M2": {
        "name": "hfl/chinese-electra-180g-small",
        "n_freeze": 0,  # 12M, 12 层, 全部微调
        "epochs": 3,
        "batch_size": 32,
        "lr": 5e-5,
        "max_len": 16,
        "estimated_time_min": 30,
    },
    "M3": {
        "name": "bert-base-chinese",
        "n_freeze": 6,  # 12 层, 冻前 6 训后 6 (2x 加速)
        "epochs": 2,
        "batch_size": 16,
        "lr": 2e-5,
        "max_len": 16,
        "estimated_time_min": 120,
    },
}


def run_train(model_key: str, log_path: str) -> int:
    """启动训练后台进程"""
    cfg = MODELS[model_key]
    cmd = [
        "python", "-X", "utf8", "-u",
        os.path.join(PROJECT_ROOT, "scripts", "train_bert_intent.py"),
        "--model", model_key,
        "--epochs", str(cfg["epochs"]),
        "--batch_size", str(cfg["batch_size"]),
        "--lr", str(cfg["lr"]),
        "--max_len", str(cfg["max_len"]),
        "--n_freeze", str(cfg["n_freeze"]),
        "--early_stop_patience", "1",  # 早停 1 epoch
    ]
    print(f"启动 {model_key}: {' '.join(cmd)}", flush=True)
    # 用 PowerShell Start-Process 后台启动
    ps_cmd = (
        f"Start-Process -FilePath 'python.exe' "
        f"-ArgumentList @({(' '.join(f'\"{c}\",' for c in cmd)).rstrip(',')}) "
        f"-WorkingDirectory '{PROJECT_ROOT}' "
        f"-RedirectStandardOutput '{log_path}' "
        f"-RedirectStandardError '{log_path}.err' "
        f"-WindowStyle Hidden -PassThru | Select-Object -ExpandProperty Id"
    )
    # 用 subprocess 调 powershell
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    print(f"  PowerShell stdout: {r.stdout.strip()}", flush=True)
    if r.stderr:
        print(f"  PowerShell stderr: {r.stderr.strip()[:200]}", flush=True)
    # 从 stdout 提取 PID
    import re
    m = re.search(r"\d+", r.stdout)
    return int(m.group()) if m else -1


def wait_for_done(model_key: str, timeout_min: int):
    """等训练完成 (轮询 status.json)"""
    short_name = MODELS[model_key]['name'].split('/')[-1]
    out_dir = os.path.join(PROJECT_ROOT, "models", f"{model_key}-{short_name}")
    status_path = os.path.join(out_dir, "train_status.json")
    print(f"\n[WAIT] 等 {model_key} 完成 (timeout {timeout_min}min)...", flush=True)
    t0 = time.time()
    last_print = 0
    while time.time() - t0 < timeout_min * 60:
        time.sleep(30)  # 30s 轮询
        if os.path.exists(status_path):
            with open(status_path, encoding="utf-8") as f:
                s = json.load(f)
            if s.get("stage") == "done":
                print(f"  [DONE] {model_key}: val={s.get('val_acc', 0)*100:.2f}%, holdout={s.get('holdout_acc', 0)*100:.2f}%", flush=True)
                return s
            # 每 5 分钟报一次
            elapsed = time.time() - t0
            if elapsed - last_print > 300:
                last_print = elapsed
                print(f"  [{elapsed/60:.0f}min] {model_key} stage={s.get('stage')}, val={s.get('val_acc', 0)*100:.2f}%", flush=True)
    print(f"  [TIMEOUT] {model_key} 超时 {timeout_min}min", flush=True)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=["M1", "M2"], help="要跑的模型 (默认 M1+M2 并行后台)")
    parser.add_argument("--sequential", action="store_true", help="串行跑 (默认并行)")
    args = parser.parse_args()

    procs = []
    for m in args.models:
        log_path = os.path.join(PROJECT_ROOT, f"train_{m}.log")
        pid = run_train(m, log_path)
        if pid > 0:
            procs.append((m, pid, log_path))
        time.sleep(2)  # 错开启动, 避免 CPU 抢

    # 配 cron 监控
    print(f"\n已启动 {len(procs)} 个训练: {procs}", flush=True)
    print("已配 cron bert-train-monitor 每 5min 自检", flush=True)

    # 等完成
    results = {}
    for m, pid, log_path in procs:
        cfg = MODELS[m]
        r = wait_for_done(m, cfg["estimated_time_min"] * 3)  # 3x 预计时间
        if r:
            results[m] = r

    # 写对比表
    if results:
        report_path = os.path.join(PROJECT_ROOT, "data", "model_benchmark_v360.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n[BENCHMARK] 完成, 结果写入 {report_path}", flush=True)
        for m, r in results.items():
            print(f"  {m}: val={r.get('val_acc', 0)*100:.2f}%, holdout={r.get('holdout_acc', 0)*100:.2f}%, time={r.get('total_time', 0)/60:.0f}min", flush=True)


if __name__ == "__main__":
    main()
