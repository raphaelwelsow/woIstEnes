"""Demo: steuert den laufenden Android-Emulator automatisiert."""
import time
import uiautomator2 as u2

d = u2.connect()  # verbindet sich mit emulator-5554
print("Gerät:", d.info["productName"], "| Bildschirm:", d.window_size())

d.screen_on()
d.press("home")
d.app_start("com.android.settings")
time.sleep(2)
d.screenshot("screenshots/01_einstellungen.png")

# Element über seinen sichtbaren Text finden und antippen
d(scrollable=True).scroll.to(textContains="About")
d(textContains="About").click()
time.sleep(1)
d.screenshot("screenshots/02_ueber_telefon.png")

d.press("home")
print("Fertig – Screenshots in ./screenshots")
