param(
  [string]$ApiBase = "http://localhost:8000"
)

$case = Invoke-RestMethod -Method Post -Uri "$ApiBase/api/cases" -ContentType "application/json" -Body '{"name":"Smoke Test","examiner":"MIST"}'
Invoke-RestMethod -Method Post -Uri "$ApiBase/api/cases/$($case.id)/questions" -ContentType "application/json" -Body '{"text":"How many ZIP files are present?"}'
$report = Invoke-RestMethod -Method Post -Uri "$ApiBase/api/cases/$($case.id)/analyze" -ContentType "application/json" -Body '{"learning_mode":true,"include_gui_steps":true,"include_cli_verification":true}'
$report | ConvertTo-Json -Depth 8
