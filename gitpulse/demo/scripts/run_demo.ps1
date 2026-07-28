param(
  [string]$DemoDir = "$env:TEMP\gitpulse-demo"
)

python demo/create_demo_repo.py --output $DemoDir
Set-Location $DemoDir
gitpulse doctor
git add .
gitpulse check
