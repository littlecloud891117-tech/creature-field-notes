# Creature Field Notes

這是自營內容站的公開原始碼 repo。正式站使用 Blogger，因為 Blogger 是 AdSense host partner。

GitHub Pages 只作部署前預覽，不是營利 hosting。

未核准草稿、中文審閱副本與人類創意貢獻紀錄不可放入本 repo。這些檔案只留在 `C:\Projects\Agent-serial\`。

## 本機檢查

```powershell
python tools\check_site.py
```

## 首次設定 Blogger

在 Windows 執行下列檔案。即使設定失敗，視窗也會保留錯誤訊息。

```powershell
tools\setup-blogger.cmd
```

也可以使用 Git Bash：

```bash
./tools/setup-blogger.sh
```

精靈會設定 Blogger 的 email 發文功能與 Gmail App Password。

本流程不使用 Google Cloud 或 OAuth。發文信箱與 App Password 只存入已忽略的 `.env`。

## 發佈一回

```powershell
C:\Users\LittleCloud\.nanobot\venv\Scripts\python.exe C:\projects\Agent\scripts\publish_site.py
```

發佈工具同步 Blogger 與本 repo。它只接受 `approval.json` 中 `status` 為 `approved` 的回目。

發佈工具也核對英文正篇的 SHA-256。未核准草稿與中文審閱副本不會進入公開位置。

工具會先記錄 `sending` 狀態，再傳送 email。若傳送結果不明，工具會停止，避免自動重複發文。
