# Mac 與 iPhone 自用版操作

本分支增加局部擷取、每房間自動照片上限、保存階段顯示與資料檢查工具。
`personal-room-rebuild` 負責串接兩個 skill；img2threejs 在電腦上的代理工具中
建立個別物件，不是在 iPhone 內執行，也不代表掃描失敗根因已修復。

## 取得此版本

新下載：

```sh
git clone --branch codex/personal-capture-img2threejs https://github.com/cloud9tw/3d-model-anything.git
cd 3d-model-anything
```

若 Mac 已有自己的 fork checkout，先保留現有未提交變更，再執行：

```sh
git fetch origin
git switch codex/personal-capture-img2threejs
git pull --ff-only
```

確認 `origin` 指向 `cloud9tw/3d-model-anything`。這是待實機驗證的功能分支，
不是已通過實機掃描驗收的版本。

## 編譯 iPhone App

安裝 Xcode 並完成首次啟動；掃描裝置需支援 LiDAR、iOS 17 以上。
Homebrew 已可使用時：

```sh
brew install xcodegen
cd apps/house-capture
xcodegen generate
open HouseCapture.xcodeproj
```

在 Xcode 的 Signing & Capabilities 選自己的 Team 與唯一 Bundle Identifier，
接上 iPhone，依裝置提示啟用開發者模式後選該裝置 Run。
重新執行 xcodegen 會重新產生專案；個人簽署設定不要提交到公開 GitHub。

## 先測一個小區域

1. 選 **Partial area**，自動照片先保留預設 **60**；可在開始前調成 0、20、40 等，最高 120。0 表示只用手動快門。
2. 移動到不同位置觀察要保留的區域，避免只站在原地旋轉或追求照片數。
3. **Photo coverage** 是已觀測表面的照片覆蓋率，不是房間完成度，也不保證幾何正確。
4. 有足夠可檢查的資料時，按 **Save current capture**；不需要等到三面牆或 100%。
5. 自動照片達上限後，量測仍繼續，手動快門仍可補拍。上限只計成功保存的自動照片，失敗寫入不占用配額；每房間重新計算。
6. 保存時會顯示照片、網格、RoomPlan、索引或位置地圖等目前階段。若停住，記下階段、裝置與時間，保留原始匯出資料供診斷。

選 **Whole room** 時，原有房間品質提示仍可參考，但保存按鈕同樣不以提示達標為條件。
局部擷取沒有量到的牆面與尺寸必須保持「未量測」，不能用補模型取代實測聲明。

## 準備重建工具

回到 repository 根目錄。Node.js 需 22.12 以上；Python 需 3.10 以上。

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install Pillow
npm ci
npx --yes img2threejs@latest install --host codex
npx --yes img2threejs@latest doctor
```

依官方要求重啟 Codex，並以本 repository 為工作目錄。安裝器若報告已存在的
非管理連結，先閱讀訊息，不要自動刪除。官方 CLI 目前僅支援 macOS／Linux。
基礎 skill 的實際版本由安裝器決定；記下 doctor 結果。不要安裝需要私有
存取權的 environment 外掛。此 repo 的橋接 skill 在 `.agents/skills/personal-room-rebuild/`。

## 檢查現有的兩百多張照片

從 iPhone 匯出原始房間 ZIP，在本機解壓到 `data/captures-in/my-session/`。
該資料夾應直接包含 `manifest.json`；不要只匯出 JPG，也不要把不同 session
的照片混進同一資料夾。所有私人輸入、報告與比較圖片留在被 Git 忽略的資料夾。

先看 manifest 的房間編號：

```sh
python -c 'import json; from pathlib import Path; m=json.loads(Path("data/captures-in/my-session/manifest.json").read_text()); print([(r["index"], r.get("name")) for r in m["rooms"]])'
```

以下以原始房間編號 **7** 為例，請改成上一步顯示的實際編號：

```sh
python .agents/skills/scan-to-threejs/scripts/assess_capture.py \
  data/captures-in/my-session --room 7 --max-photos 24 \
  --out data/captures/my-session/evidence.json
```

此工具不修改原始照片；報告包含選取的照片、排除理由、相機姿態、雜湊與
未知的品質訊號。若輸出檔已存在，換一個新報告檔名。`blocked` 的退出碼是 2，
表示目前沒有可接受的帶姿態參考照片；仍會保存報告供檢查。`partial` 表示
部分輸入無效或缺少可用房間量測；不是資料遺失，也不是重建已成功。

將這段交給 Mac 上的 Codex：

> 使用 $personal-room-rebuild，讀取 data/captures/my-session/evidence.json 與原始匯出包。
> 先診斷照片及座標問題，建立可信的房間骨架，再用 img2threejs 重建一件主要家具。
> 保留尺寸與相機證據，從不同視角比對。尚未量測或看不到的部分明確標為推估。
> 私人照片及重建比較圖不要上傳 GitHub。

之後執行 `npm run dev`，在本機 `http://localhost:5188` 查看代理加入的房間。
沒有實際匯出包時，這個分支不會自動出現你房間的模型。

## 驗證與回報

Mac 可執行純政策測試：

```sh
swiftc apps/house-capture/HouseCapture/CaptureQuality.swift \
  apps/house-capture/tests/CapturePolicyTests.swift -o /tmp/capture-policies
/tmp/capture-policies
python -m unittest discover -s .agents/skills/scan-to-threejs/scripts -p 'test_*.py'
npm run build
```

GitHub 的 Capture checks 另做 iOS 模擬器編譯及 App 自我測試；模擬器沒有
真實 LiDAR／相機追蹤，不能取代手機驗證。回報時附 iPhone 型號、iOS、安裝版本、
卡住的保存階段，以及原始 ZIP。不要把 ZIP 提交到這個公開 repository。

來源：
- https://github.com/img2threejs/img2threejs/blob/main/docs/INSTALL.md
- https://github.com/img2threejs/img2threejs/blob/main/SKILL.md
