package com.parilo.vpn

import android.app.Activity
import android.content.Intent
import android.net.VpnService
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import android.widget.TextView

class MainActivity : AppCompatActivity() {

    private var vpnKey: String = ""
    private lateinit var statusText: TextView

    private val vpnPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            startParilo(true)
        } else {
            Toast.makeText(this, "اجازه VPN لازم است", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val inputKey = findViewById<TextInputEditText>(R.id.inputKey)
        val btnConnect = findViewById<MaterialButton>(R.id.btnConnect)
        val btnDisconnect = findViewById<MaterialButton>(R.id.btnDisconnect)
        statusText = findViewById(R.id.statusText)

        // نمونه کلید برای تست ظاهری
        // inputKey.setText("ss://...")

        btnConnect.setOnClickListener {
            vpnKey = inputKey.text.toString().trim()
            if (vpnKey.isEmpty()) {
                inputKey.error = "کلید ss:// را وارد کن"
                return@setOnClickListener
            }
            if (!vpnKey.startsWith("ss://")) {
                inputKey.error = "کلید باید با ss:// شروع شود"
                return@setOnClickListener
            }
            prepareVpn()
        }

        btnDisconnect.setOnClickListener {
            startParilo(false)
        }

        updateStatus(PariloVpnService.isRunning)
    }

    private fun prepareVpn() {
        val intent = VpnService.prepare(this)
        if (intent != null) {
            vpnPermissionLauncher.launch(intent)
        } else {
            startParilo(true)
        }
    }

    private fun startParilo(connect: Boolean) {
        val intent = Intent(this, PariloVpnService::class.java).apply {
            action = if (connect) "CONNECT" else "DISCONNECT"
            putExtra("key", vpnKey)
        }
        startService(intent)
        // تاخیر کوتاه برای آپدیت وضعیت
        statusText.postDelayed({ updateStatus(connect) }, 800)
        Toast.makeText(this, if(connect) "در حال اتصال Parilo..." else "قطع شد", Toast.LENGTH_SHORT).show()
    }

    private fun updateStatus(connected: Boolean){
        statusText.text = if(connected) "● متصل - Parilo فعال است" else "○ قطع - آماده اتصال"
        statusText.setTextColor(if(connected) 0xFF2E7D32.toInt() else 0xFF616161.toInt())
    }
}
