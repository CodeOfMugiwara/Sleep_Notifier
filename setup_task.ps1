$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw = Join-Path $scriptDir "venv\Scripts\pythonw.exe"
$mainPy = Join-Path $scriptDir "main.py"
$taskName = "SleepNotifier"

$action = New-ScheduledTaskAction -Execute $pythonw -Argument $mainPy -WorkingDirectory $scriptDir

$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$triggerStartup = New-ScheduledTaskTrigger -AtStartup

$triggerWake = New-ScheduledTaskTrigger -AtLogOn
$triggerWake.Subscription = '<QueryList><Query Id="0" Path="System"><Select Path="System">*[System[Provider[@Name="Microsoft-Windows-Power-Troubleshooter"] and EventID=1]]</Select></Query></QueryList>'

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($triggerLogon, $triggerStartup) -Settings $settings -Principal $principal -Description "Sleep Notifier - Forces you to sleep at night"

Start-ScheduledTask -TaskName $taskName
Write-Host "Task '$taskName' created and started." -ForegroundColor Green
Write-Host "Triggers: At Logon + At Startup" -ForegroundColor Cyan
