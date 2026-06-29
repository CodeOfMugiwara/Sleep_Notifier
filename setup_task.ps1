$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw = Join-Path $scriptDir "venv\Scripts\pythonw.exe"
$mainPy = Join-Path $scriptDir "main.py"
$taskName = "SleepNotifier"

$action = New-ScheduledTaskAction -Execute $pythonw -Argument $mainPy -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Sleep Notifier - Forces you to sleep at night"

Start-ScheduledTask -TaskName $taskName
Write-Host "Task '$taskName' created and started." -ForegroundColor Green
