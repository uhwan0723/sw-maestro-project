package com.soma2026.tikitalka.presentation.dashboard

import com.soma2026.tikitalka.domain.model.Issue

data class DashboardState(
    val issues: List<Issue> = emptyList(),
    val isLoading: Boolean = false,
    val isLoadingMore: Boolean = false,
    val currentPage: Int = 0,
    val isLastPage: Boolean = false,
    val errorMessage: String? = null,
)
