package com.soma2026.tikitalka.di

import org.koin.core.KoinApplication
import org.koin.core.context.startKoin
import org.koin.core.module.Module

fun initKoin(
    baseUrl: String,
    isDebug: Boolean = false,
    extraModules: List<Module> = emptyList(),
    appDeclaration: KoinApplication.() -> Unit = {},
): KoinApplication = startKoin {
    appDeclaration()
    modules(
        platformModule,
        networkModule(baseUrl, isDebug),
        repositoryModule,
        useCaseModule,
        viewModelModule,
        *extraModules.toTypedArray(),
    )
}