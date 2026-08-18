# Creature Field Notes

這是自營內容站的公開輸出 repo。GitHub Pages 從 `main` 根目錄直接發佈。

未核准草稿、中文審閱副本與人類創意貢獻紀錄不可放入本 repo。這些檔案只留在 `C:\Projects\Agent-serial\`。

## 本機檢查

```powershell
python tools\check_site.py
```

## 發佈一回

```powershell
python tools\publish.py --source C:\Projects\Agent-serial
git add -A
git commit -m "feat: 發佈連載回目"
git push
```

`publish.py` 只接受 `approval.json` 中 `status` 為 `approved` 的回目。它也核對英文正篇的 SHA-256。
