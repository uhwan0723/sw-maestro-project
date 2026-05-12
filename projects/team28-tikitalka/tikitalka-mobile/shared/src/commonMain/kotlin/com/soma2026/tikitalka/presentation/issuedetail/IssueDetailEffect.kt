package com.soma2026.tikitalka.presentation.issuedetail

sealed class IssueDetailEffect {
    data object NavigateBack : IssueDetailEffect()
    data class ShowError(val message: String) : IssueDetailEffect()
}