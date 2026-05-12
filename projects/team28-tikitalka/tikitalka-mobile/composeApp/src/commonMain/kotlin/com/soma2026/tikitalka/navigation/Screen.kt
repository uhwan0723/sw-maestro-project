package com.soma2026.tikitalka.navigation

sealed class Screen(val route: String) {
    data object Dashboard : Screen("dashboard")
    data object Chat : Screen("chat")
    data object IssueDetail : Screen("issue_detail/{id}") {
        fun createRoute(id: String) = "issue_detail/$id"
    }
}
