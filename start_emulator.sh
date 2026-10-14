#!/bin/zsh
# Startet den Android-Emulator und wartet, bis er hochgefahren ist.
# Nutzung: ./start_emulator.sh            (mit Fenster)
#          ./start_emulator.sh headless   (ohne Fenster)
export ANDROID_HOME=$HOME/Library/Android/sdk
export JAVA_HOME=$HOME/Android/jdk/Contents/Home
ADB=$ANDROID_HOME/platform-tools/adb

EXTRA=()
[[ "$1" == "headless" ]] && EXTRA=(-no-window -no-audio)

nohup $ANDROID_HOME/emulator/emulator -avd testphone -no-boot-anim "${EXTRA[@]}" > $HOME/Android/emulator.log 2>&1 &
$ADB wait-for-device
until [[ "$($ADB shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]]; do sleep 2; done
echo "Emulator bereit: $($ADB devices | grep emulator)"
