# Parilo VPN - پاريلو

اپلیکیشن اندروید VPN شخصی با نام **Parilo**

### چی میگیری؟
پروژه کامل اندروید استودیو + آماده برای خروجی APK
- نام برنامه: Parilo
- پکیج: com.parilo.vpn
- زبان: Kotlin + Android VpnService
- اتصال با کلید Outline/Shadowsocks `ss://...`

### چطور APK بسازی؟ (۲ دقیقه)
این پروژه آماده است، چون ساخت APK نیاز به Android Studio داره:

1. برنامه **Android Studio** رو نصب کن (https://developer.android.com/studio)
2. پوشه `Parilo` رو با Android Studio باز کن (Open Project)
3. از منو: `Build` -> `Build APK(s)` -> بعد از تمام شدن، روی `locate` بزن
4. فایل `Parilo.apk` آماده است و روی گوشی نصب میشه

> اگر Android Studio نداری، میتونی همین کد رو به یک دوست که اندروید استودیو داره بدی یا از سایت https://appetize.io برای تست آنلاین استفاده کنی.

### چطور کار میکنه؟
1. سرور Outline که در آموزش قبلی گرفتی، کلید `ss://...` رو کپی کن
2. برنامه Parilo رو باز کن، کلید رو Paste کن و `اتصال` بزن
3. اندروید ازت اجازه VPN میخواد -> تایید کن

### ساختار پروژه
```
Parilo/
├── app/src/main/java/com/parilo/vpn/
│   ├── MainActivity.kt (رابط کاربری)
│   └── PariloVpnService.kt (سرویس VPN)
├── app/src/main/res/layout/activity_main.xml
└── app/src/main/AndroidManifest.xml
```

> نکته: این نسخه یک کلاینت Shadowsocks ساده است. برای کار واقعی حتما باید کلید سرور شخصی خودت رو وارد کنی.

ساخته شده برای آموزش و استفاده شخصی.
