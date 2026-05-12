package com.soma2026.tikitalka.data.local

import android.content.Context
import android.provider.Settings
import com.soma2026.tikitalka.domain.repository.DeviceIdRepository

class AndroidDeviceIdRepository(
    private val context: Context,
) : DeviceIdRepository {

    override suspend fun getDeviceId(): String =
        Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
            ?: java.util.UUID.randomUUID().toString()
}