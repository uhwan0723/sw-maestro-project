package com.soma2026.tikitalka.presentation.issuedetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.soma2026.tikitalka.domain.service.TranslationLanguage
import com.soma2026.tikitalka.domain.service.TranslationService
import com.soma2026.tikitalka.domain.usecase.GetIssueDetailUseCase
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class IssueDetailViewModel(
    private val getIssueDetail: GetIssueDetailUseCase,
    private val translationService: TranslationService,
) : ViewModel() {

    private val _state = MutableStateFlow(IssueDetailState())
    val state: StateFlow<IssueDetailState> = _state.asStateFlow()

    private val _effect = Channel<IssueDetailEffect>(Channel.BUFFERED)
    val effect = _effect.receiveAsFlow()

    private var translationJob: Job? = null

    fun load(id: String) {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorMessage = null) }
            getIssueDetail(id)
                .onSuccess { issue ->
                    _state.update { it.copy(issue = issue, isLoading = false) }
                }
                .onFailure { error ->
                    val message = error.message ?: "뉴스를 불러오지 못했습니다"
                    _state.update { it.copy(isLoading = false, errorMessage = message) }
                    _effect.send(IssueDetailEffect.ShowError(message))
                }
        }
    }

    fun handleIntent(intent: IssueDetailIntent) {
        when (intent) {
            is IssueDetailIntent.NavigateBack -> {
                viewModelScope.launch { _effect.send(IssueDetailEffect.NavigateBack) }
            }
            is IssueDetailIntent.SelectLanguage -> selectLanguage(intent.language)
        }
    }

    private fun selectLanguage(language: TranslationLanguage) {
        if (_state.value.selectedLanguage == language) return
        translationJob?.cancel()
        _state.update { it.copy(selectedLanguage = language, translatedContent = null, isTranslating = false) }

        if (language == TranslationLanguage.ENGLISH) return

        val content = _state.value.issue?.originalContent ?: return
        translationJob = viewModelScope.launch {
            _state.update { it.copy(isTranslating = true) }
            translationService.translate(content, language)
                .onSuccess { translated ->
                    if (_state.value.selectedLanguage == language) {
                        _state.update { it.copy(translatedContent = translated, isTranslating = false) }
                    }
                }
                .onFailure { error ->
                    _state.update { it.copy(isTranslating = false) }
                    _effect.send(IssueDetailEffect.ShowError(error.message ?: "번역에 실패했습니다"))
                }
        }
    }
}