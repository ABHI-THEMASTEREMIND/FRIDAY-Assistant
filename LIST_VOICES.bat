@echo off
powershell -NoProfile -Command "Add-Type -AssemblyName System.Speech; $voice = New-Object System.Speech.Synthesis.SpeechSynthesizer; $voice.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo | Select-Object Name, Gender, Culture } | Format-Table -AutoSize"
echo.
echo Copy or take a picture of the British male voice name you want FRIDAY to use.
pause
