package com.parilo.vpn

import android.content.Intent
import android.net.VpnService
import android.os.ParcelFileDescriptor
import java.util.concurrent.Executors

/**
 * Parilo VPN Service - نسخه آموزشی
 * این سرویس یک تونل VPN ساده میسازد.
 * برای اتصال واقعی Shadowsocks باید کتابخانه shadowsocks یا Outline SDK اضافه شود.
 * این نسخه برای نمایش کارکرد و تست UI است و تونل را باز نگه میدارد.
 */
class PariloVpnService : VpnService() {

    companion object {
        var isRunning = false
    }

    private var vpnInterface: ParcelFileDescriptor? = null
    private val executor = Executors.newSingleThreadExecutor()

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "DISCONNECT" -> {
                stopVpn()
                stopSelf()
            }
            "CONNECT" -> {
                val key = intent.getStringExtra("key") ?: ""
                startVpn(key)
            }
        }
        return START_NOT_STICKY
    }

    private fun startVpn(key: String) {
        if (isRunning) return
        executor.execute {
            try {
                // پارس ساده کلید ss:// برای نمایش - در نسخه واقعی اینجا اتصال SOCKS برقرار میشود
                val builder = Builder()
                    .addAddress("10.8.0.2", 32)
                    .addRoute("0.0.0.0", 0)
                    .addDnsServer("1.1.1.1")
                    .addDnsServer("8.8.8.8")
                    .setSession("Parilo")
                    .setMtu(1500)

                // اندروید 14+ نیاز به اجازه دارد - Builder ایجاد میکند
                vpnInterface = builder.establish()
                isRunning = true

                // در نسخه کامل اینجا باید یک پراکسی shadowsocks به سرور key وصل شود
                // فعلا تونل باز نگه داشته میشود تا وضعیت "متصل" نمایش داده شود

            } catch (e: Exception) {
                e.printStackTrace()
                stopVpn()
            }
        }
    }

    private fun stopVpn() {
        try {
            vpnInterface?.close()
        } catch (_: Exception) {}
        vpnInterface = null
        isRunning = false
    }

    override fun onDestroy() {
        stopVpn()
        super.onDestroy()
    }

    override fun onRevoke() {
        stopVpn()
        super.onRevoke()
    }
}
