package com.soma2026.tikitalka.presentation.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.soma2026.tikitalka.domain.model.ChatMessage
import com.soma2026.tikitalka.domain.model.MessageRole
import com.soma2026.tikitalka.domain.usecase.GetChatHistoryUseCase
import com.soma2026.tikitalka.domain.usecase.GetDeviceIdUseCase
import com.soma2026.tikitalka.domain.usecase.SendChatMessageUseCase
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.datetime.Clock
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toLocalDateTime

class ChatViewModel(
    private val sendChatMessage: SendChatMessageUseCase,
    private val getChatHistory: GetChatHistoryUseCase,
    private val getDeviceId: GetDeviceIdUseCase,
) : ViewModel() {

    private var deviceId: String = ""

    private val _state = MutableStateFlow(ChatState())
    val state: StateFlow<ChatState> = _state.asStateFlow()

    private val _effect = Channel<ChatEffect>(Channel.BUFFERED)
    val effect = _effect.receiveAsFlow()

    init {
        viewModelScope.launch {
            deviceId = getDeviceId()
            loadHistory()
        }
    }

    fun handleIntent(intent: ChatIntent) {
        when (intent) {
            is ChatIntent.UpdateInput -> _state.update { it.copy(inputText = intent.text) }
            is ChatIntent.SendMessage -> sendMessage()
            is ChatIntent.SelectSuggestedQuestion -> sendMessage(intent.question)
        }
    }

    private fun loadHistory() {
        viewModelScope.launch {
            _state.update { it.copy(isLoadingHistory = true) }
            getChatHistory(deviceId)
                .onSuccess { messages ->
                    _state.update { state ->
                        if (state.messages.isEmpty()) {
                            state.copy(messages = messages, isLoadingHistory = false)
                        } else {
                            state.copy(isLoadingHistory = false)
                        }
                    }
                }
                .onFailure { error ->
                    _state.update { it.copy(isLoadingHistory = false) }
                    _effect.send(ChatEffect.ShowError(error.message ?: "대화 이력을 불러오지 못했습니다"))
                }
        }
    }

    private fun sendMessage(overrideText: String? = null) {
        val text = (overrideText ?: _state.value.inputText).trim()
        if (text.isBlank() || _state.value.isSending) return

        val userMessage = ChatMessage(
            role = MessageRole.USER,
            content = text,
            suggestedQuestion = null,
            createdAt = Clock.System.now().toLocalDateTime(TimeZone.currentSystemDefault()).toString(),
        )

        _state.update {
            it.copy(
                messages = it.messages + userMessage,
                inputText = "",
                isSending = true,
            )
        }

        viewModelScope.launch {
            sendChatMessage(deviceId, text)
                .onSuccess { response ->
                    _state.update {
                        it.copy(
                            messages = it.messages + response,
                            isSending = false,
                        )
                    }
                }
                .onFailure { error ->
                    _state.update { it.copy(isSending = false) }
                    _effect.send(ChatEffect.ShowError(error.message ?: "메시지 전송에 실패했습니다"))
                }
        }
    }
}