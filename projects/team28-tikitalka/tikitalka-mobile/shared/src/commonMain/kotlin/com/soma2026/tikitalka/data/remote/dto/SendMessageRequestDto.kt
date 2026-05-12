package com.soma2026.tikitalka.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class SendMessageRequestDto(
    val deviceId: String,
    val message: String,
)