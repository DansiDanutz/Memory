@echo off
cd C:\Users\dansi\Desktop\Memory
git add .
git commit -m "Auto-sync: %date% %time%"
git push origin master
echo Synced at %date% %time%