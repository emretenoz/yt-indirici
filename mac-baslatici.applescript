set appDir to do shell script "dirname " & quoted form of POSIX path of (path to me)
set ready to do shell script "test -x " & quoted form of (appDir & "/.venv/bin/python") & " && echo yes || echo no"
if ready is "no" then
	display dialog "İlk açılış: gerekli bileşenler kurulacak. Bu birkaç dakika sürebilir. Bir Terminal penceresi açılacak; kurulum bitince tarayıcı kendiliğinden açılır." buttons {"Tamam"} default button 1 with title "YT İndirici"
	do shell script "open -a Terminal " & quoted form of (appDir & "/Baslat (Mac).command")
else
	do shell script "cd " & quoted form of appDir & " && nohup /bin/bash ./calistir.sh > .yt-indirici.log 2>&1 &"
end if
