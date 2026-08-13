param(
  [string]$DemoDir = "$env:TEMP\gitplus-demo"
)

python demo/create_demo_repo.py --output $DemoDir
Set-Location $DemoDir
gitplus doctor
git add .
gitplus check
