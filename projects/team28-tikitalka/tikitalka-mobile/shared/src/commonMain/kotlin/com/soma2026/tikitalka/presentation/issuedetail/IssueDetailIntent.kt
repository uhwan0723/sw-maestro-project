package com.soma2026.tikitalka.presentation.issuedetail

import com.soma2026.tikitalka.domain.service.TranslationLanguage

sealed class IssueDetailIntent {
    data object NavigateBack : IssueDetailIntent()
    data class SelectLanguage(val language: TranslationLanguage) : IssueDetailIntent()
}