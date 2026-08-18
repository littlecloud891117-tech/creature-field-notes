# Creature Field Notes

這是自營內容站的公開原始碼 repo。正式站使用 Blogger，因為 Blogger 是 AdSense host partner。

GitHub Pages 只作部署前預覽，不是營利 hosting。

未核准草稿、中文審閱副本與人類創意貢獻紀錄不可放入本 repo。這些檔案只留在 `C:\Projects\Agent-serial\`。

## 本機檢查

```powershell
python tools\check_site.py
```

## 首次設定 Blogger

使用 Git Bash 執行：

```bash
./tools/setup-blogger.sh
```

精靈會建立 Blogger OAuth 授權。OAuth client 與 token 只存入 `.secrets/`。

## 發佈一回

```powershell
C:\Users\LittleCloud\.nanobot\venv\Scripts\python.exe C:\projects\Agent\scripts\publish_site.py
```

發佈工具同步 Blogger 與本 repo。它只接受 `approval.json` 中 `status` 為 `approved` 的回目。

發佈工具也核對英文正篇的 SHA-256。未核准草稿與中文審閱副本不會進入公開位置。
