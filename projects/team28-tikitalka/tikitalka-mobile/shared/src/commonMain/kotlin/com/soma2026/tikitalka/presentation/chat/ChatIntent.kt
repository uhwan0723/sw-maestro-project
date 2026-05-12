package com.soma2026.tikitalka.presentation.chat

sealed class ChatIntent {
    data class UpdateInput(val text: String) : ChatIntent()
    data object SendMessage : ChatIntent()
    data class SelectSuggestedQuestion(val question: String) : ChatIntent()
}