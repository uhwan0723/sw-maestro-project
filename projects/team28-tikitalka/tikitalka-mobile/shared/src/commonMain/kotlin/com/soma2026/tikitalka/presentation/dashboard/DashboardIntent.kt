package com.soma2026.tikitalka.presentation.dashboard

sealed class DashboardIntent {
    data object LoadIssues : DashboardIntent()
    data object LoadMore : DashboardIntent()
    data class SelectIssue(val issueId: String) : DashboardIntent()
    data object Refresh : DashboardIntent()
}
