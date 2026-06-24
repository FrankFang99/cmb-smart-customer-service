$ErrorActionPreference = 'Continue'
Set-Location 'D:\Learning\AI\面试\AI智能客服'
$out = 'data\v3110_final_run.txt'
"=== v3.11.0 FINAL: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -FilePath $out -Encoding UTF8
"=== Step 1: D v3.2 dedup (1076 条) ===" | Out-File -FilePath $out -Append -Encoding UTF8
try {
    python scripts/run_v3110_regression.py 2>&1 | Out-File -FilePath $out -Append -Encoding UTF8
} catch {
    "D v3.2 Exception: $_" | Out-File -FilePath $out -Append -Encoding UTF8
}
"=== Step 2: D v3.3 新样本 (206 条) ===" | Out-File -FilePath $out -Append -Encoding UTF8
try {
    python scripts/run_v3110_round1.py 2>&1 | Out-File -FilePath $out -Append -Encoding UTF8
} catch {
    "D v3.3 Exception: $_" | Out-File -FilePath $out -Append -Encoding UTF8
}
"=== Finished: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -FilePath $out -Append -Encoding UTF8
