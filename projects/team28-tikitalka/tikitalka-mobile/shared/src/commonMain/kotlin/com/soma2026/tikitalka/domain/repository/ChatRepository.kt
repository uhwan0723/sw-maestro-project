package com.soma2026.tikitalka.domain.repository

import com.soma2026.tikitalka.domain.model.ChatMessage

interface ChatRepository {
    suspend fun sendMessage(deviceId: String, message: String): Result<ChatMessage>

    suspend fun getChatHistory(deviceId: String): Result<List<ChatMessage>>
}