package com.soma2026.tikitalka.di

import com.soma2026.tikitalka.presentation.chat.ChatViewModel
import com.soma2026.tikitalka.presentation.dashboard.DashboardViewModel
import com.soma2026.tikitalka.presentation.issuedetail.IssueDetailViewModel
import org.koin.core.module.dsl.viewModelOf
import org.koin.dsl.module

val appModule = module {
    viewModelOf(::DashboardViewModel)
    viewModelOf(::ChatViewModel)
    viewModelOf(::IssueDetailViewModel)
}