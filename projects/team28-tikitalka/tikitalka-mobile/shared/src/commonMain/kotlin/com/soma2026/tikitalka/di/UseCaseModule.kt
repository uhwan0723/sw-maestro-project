package com.soma2026.tikitalka.di

import com.soma2026.tikitalka.domain.usecase.GetChatHistoryUseCase
import com.soma2026.tikitalka.domain.usecase.GetDeviceIdUseCase
import com.soma2026.tikitalka.domain.usecase.GetIssueDetailUseCase
import com.soma2026.tikitalka.domain.usecase.GetIssuesUseCase
import com.soma2026.tikitalka.domain.usecase.SendChatMessageUseCase
import org.koin.dsl.module

val useCaseModule = module {
    factory { GetIssuesUseCase(get()) }
    factory { GetIssueDetailUseCase(get()) }
    factory { SendChatMessageUseCase(get()) }
    factory { GetChatHistoryUseCase(get()) }
    factory { GetDeviceIdUseCase(get()) }
}