package com.soma2026.tikitalka.data.repository

import com.soma2026.tikitalka.data.remote.api.ChatApi
import com.soma2026.tikitalka.data.remote.dto.toDomain
import com.soma2026.tikitalka.domain.model.ChatMessage
import com.soma2026.tikitalka.domain.repository.ChatRepository

class ChatRepositoryImpl(
    private val api: ChatApi,
) : ChatRepository {

    override suspend fun sendMessage(deviceId: String, message: String): Result<ChatMessage> =
        runCatching {
            api.sendMessage(deviceId, message).toDomain()
        }

    override suspend fun getChatHistory(deviceId: String): Result<List<ChatMessage>> =
        runCatching {
            api.getChatHistory(deviceId).map { it.toDomain() }
        }
}
