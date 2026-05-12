package com.soma2026.tikitalka.domain.model

data class ChatMessage(
    val role: MessageRole,
    val content: String,
    val suggestedQuestion: String?,
    val createdAt: String,
)