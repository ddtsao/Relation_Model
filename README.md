# SPS 實驗執行指南

下載整個專案並解壓縮，安裝 **Python 3.10**。不需要Git、MATLAB或論文PDF。

## 1. 確認目錄

```text
專案根目錄/
├── Relation/                 # 已附作者原碼及LICENSE.txt
├── table_reproduction/       # 實驗程式
├── vendor_manifest.json      # 作者檔案SHA256核對清單
├── VENDOR.md                 # 原碼來源與版本
├── requirements-reproduce.txt
├── README.md
└── .gitignore
```

請完整保留Relation及vendor_manifest.json，不要修改作者檔案。核對會忽略Windows的CRLF/LF差異，不依賴.git資料夾。

## 2. 安裝及準備（首次執行）

在專案根目錄開啟Windows PowerShell：

```powershell
py -3.10 -m venv .experiment-venv
& .experiment-venv/Scripts/python.exe -m pip install -r requirements-reproduce.txt
& .experiment-venv/Scripts/python.exe -B table_reproduction/prepare.py
```

prepare.py核對作者檔案並建立1920次實驗的工作清單，不會讀取PDF。

## 3. 執行實驗

先試跑LZG01、種子1，共16次：

```powershell
& .experiment-venv/Scripts/python.exe -B table_reproduction/run.py --workers 1 --seeds 1 --problems LZG01 --out results
```

完整跑四題、各30次，共1920次：

```powershell
& .experiment-venv/Scripts/python.exe -B table_reproduction/run.py --workers 2 --seeds 30 --out results
```

設定為SPS、20維、族群50、每次2000 FE；只跑LZG01–04。GA／EDA／DE／CoDE各比較BASE／FLS／FVS／CVS，CoDE維持第一版current-to-rand。未加入後續診斷或修正。

已完成工作會略過，中斷後用同一命令恢復。不要同時啟動兩份批次；完整實驗可能需要數小時，記憶體不足時改用workers 1。

## 4. 查看結果

完成後自動產生：

- `table_reproduction/results/table_II.csv`：GA。
- `table_reproduction/results/table_III.csv`：EDA。
- `table_reproduction/results/table_IV.csv`：DE。
- `table_reproduction/results/table_V.csv`：CoDE。
- `table_reproduction/meeting_report.html`：結果報告。

進度看`results/status.json`，完成度看`results/audit.json`。表格mean是平均最佳目標值，std是樣本標準差，n是已完成次數；完整實驗各格應為30。試跑時顯示整體未完成是正常的。

手動更新報告：

```powershell
$env:MPLCONFIGDIR="$PWD/tmp/matplotlib"
& .experiment-venv/Scripts/python.exe -B table_reproduction/analyze.py
```

本倉庫不附任何舊實驗數據或論文表格數據，PDF不是執行必要檔案。預設paper_mean與difference_percent欄位留白，不影響本次結果生成。不同電腦不保證數值逐位相同，請維持固定套件版本。

所有結果留在本機，不需上傳GitHub。上傳整份程式時，請包含Relation/、vendor_manifest.json與VENDOR.md。

