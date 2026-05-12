package com.soma2026.tikitalka.presentation.issuedetail

import com.soma2026.tikitalka.domain.model.Issue
import com.soma2026.tikitalka.domain.service.TranslationLanguage

data class IssueDetailState(
    val issue: Issue? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val selectedLanguage: TranslationLanguage = TranslationLanguage.ENGLISH,
    val translatedContent: String? = null,
    val isTranslating: Boolean = false,
)