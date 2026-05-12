package com.soma2026.tikitalka.presentation.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.soma2026.tikitalka.domain.usecase.GetIssuesUseCase
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class DashboardViewModel(
    private val getIssues: GetIssuesUseCase,
) : ViewModel() {

    private val _state = MutableStateFlow(DashboardState())
    val state: StateFlow<DashboardState> = _state.asStateFlow()

    private val _effect = Channel<DashboardEffect>(Channel.BUFFERED)
    val effect = _effect.receiveAsFlow()

    init {
        handleIntent(DashboardIntent.LoadIssues)
    }

    fun handleIntent(intent: DashboardIntent) {
        when (intent) {
            is DashboardIntent.LoadIssues -> loadIssues()
            is DashboardIntent.LoadMore -> loadMore()
            is DashboardIntent.SelectIssue -> navigateToDetail(intent.issueId)
            is DashboardIntent.Refresh -> loadIssues()
        }
    }

    private fun loadIssues() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorMessage = null) }
            getIssues(page = 0)
                .onSuccess { paged ->
                    _state.update {
                        it.copy(
                            issues = paged.content,
                            isLoading = false,
                            errorMessage = null,
                            currentPage = paged.page,
                            isLastPage = paged.page >= paged.totalPages - 1,
                        )
                    }
                }
                .onFailure { error ->
                    val message = error.message ?: "알 수 없는 오류"
                    _state.update { it.copy(isLoading = false, errorMessage = message) }
                    _effect.send(DashboardEffect.ShowError(message))
                }
        }
    }

    private fun loadMore() {
        val current = _state.value
        if (current.isLoadingMore || current.isLastPage) return

        viewModelScope.launch {
            _state.update { it.copy(isLoadingMore = true) }
            getIssues(page = current.currentPage + 1)
                .onSuccess { paged ->
                    _state.update {
                        it.copy(
                            issues = it.issues + paged.content,
                            isLoadingMore = false,
                            currentPage = paged.page,
                            isLastPage = paged.page >= paged.totalPages - 1,
                        )
                    }
                }
                .onFailure { error ->
                    _state.update { it.copy(isLoadingMore = false) }
                    _effect.send(DashboardEffect.ShowError(error.message ?: "알 수 없는 오류"))
                }
        }
    }

    private fun navigateToDetail(issueId: String) {
        viewModelScope.launch {
            _effect.send(DashboardEffect.NavigateToDetail(issueId))
        }
    }
}
