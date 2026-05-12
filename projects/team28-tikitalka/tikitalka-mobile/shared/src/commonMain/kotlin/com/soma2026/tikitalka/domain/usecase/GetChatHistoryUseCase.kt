package com.soma2026.tikitalka.domain.usecase

import com.soma2026.tikitalka.domain.model.ChatMessage
import com.soma2026.tikitalka.domain.repository.ChatRepository

class GetChatHistoryUseCase(
    private val repository: ChatRepository,
) {
    suspend operator fun invoke(deviceId: String): Result<List<ChatMessage>> =
        repository.getChatHistory(deviceId)
}