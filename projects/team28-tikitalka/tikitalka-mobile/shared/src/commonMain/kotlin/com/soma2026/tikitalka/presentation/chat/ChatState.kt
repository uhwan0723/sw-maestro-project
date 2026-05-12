package com.soma2026.tikitalka.presentation.chat

import com.soma2026.tikitalka.domain.model.ChatMessage

data class ChatState(
    val messages: List<ChatMessage> = emptyList(),
    val inputText: String = "",
    val isSending: Boolean = false,
    val isLoadingHistory: Boolean = false,
)