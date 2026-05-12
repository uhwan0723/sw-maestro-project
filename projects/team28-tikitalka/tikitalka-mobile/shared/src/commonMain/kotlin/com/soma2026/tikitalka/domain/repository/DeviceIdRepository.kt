package com.soma2026.tikitalka.domain.repository

interface DeviceIdRepository {
    suspend fun getDeviceId(): String
}