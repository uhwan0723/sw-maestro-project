package com.soma2026.tikitalka.di

import com.soma2026.tikitalka.data.repository.ChatRepositoryImpl
import com.soma2026.tikitalka.data.repository.IssueRepositoryImpl
import com.soma2026.tikitalka.domain.repository.ChatRepository
import com.soma2026.tikitalka.domain.repository.IssueRepository
import org.koin.dsl.module

val repositoryModule = module {
    single<IssueRepository> { IssueRepositoryImpl(get()) }
    single<ChatRepository> { ChatRepositoryImpl(get()) }
}