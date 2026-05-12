package com.soma2026.tikitalka.domain.usecase

import com.soma2026.tikitalka.domain.repository.DeviceIdRepository

class GetDeviceIdUseCase(
    private val repository: DeviceIdRepository,
) {
    suspend operator fun invoke(): String = repository.getDeviceId()
}