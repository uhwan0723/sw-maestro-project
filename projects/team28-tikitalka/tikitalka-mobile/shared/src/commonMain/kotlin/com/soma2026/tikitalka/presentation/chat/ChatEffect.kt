package com.soma2026.tikitalka.presentation.chat

sealed class ChatEffect {
    data object NavigateBack : ChatEffect()
    data class ShowError(val message: String) : ChatEffect()
}