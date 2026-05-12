package com.soma2026.tikitalka.data.remote.dto

import com.soma2026.tikitalka.domain.model.ChatMessage
import com.soma2026.tikitalka.domain.model.MessageRole
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ChatMessageDto(
    val role: String,
    val content: String,
    val suggestedQuestion: String? = null,
    @SerialName("timestamp")
    val createdAt: String,
)

fun ChatMessageDto.toDomain(): ChatMessage = ChatMessage(
    role = when (role) {
        "assistant" -> MessageRole.ASSISTANT
        else -> MessageRole.USER
    },
    content = content,
    suggestedQuestion = suggestedQuestion,
    createdAt = createdAt,
)

