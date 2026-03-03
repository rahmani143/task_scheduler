<#
PowerShell helper: shows a sample schtasks command to register the morning_brief job on Workstation Unlock.
Running the generated schtasks command may require Administrator privileges.
#>
param(
    [string]$TaskName = 'Brother_MorningBrief'
)

$exe = "python"
$script = "${PWD}\morning_brief.py"

Write-Output "Registering scheduled task: $TaskName"

$taskcmd = "schtasks /Create /TN $TaskName /TR `"$exe $script`" /SC ONLOGON /RL HIGHEST /F"
Write-Output "Command (preview): $taskcmd"
Write-Output "Run the above command in an elevated PowerShell to register the task."
