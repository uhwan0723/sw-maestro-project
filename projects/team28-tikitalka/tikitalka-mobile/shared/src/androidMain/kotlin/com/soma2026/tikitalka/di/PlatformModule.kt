package com.soma2026.tikitalka.di

import com.soma2026.tikitalka.data.local.AndroidDeviceIdRepository
import com.soma2026.tikitalka.data.service.AndroidTranslationService
import com.soma2026.tikitalka.domain.repository.DeviceIdRepository
import com.soma2026.tikitalka.domain.service.TranslationService
import org.koin.android.ext.koin.androidContext
import org.koin.core.module.Module
import org.koin.dsl.module

actual val platformModule: Module = module {
    single<DeviceIdRepository> { AndroidDeviceIdRepository(androidContext()) }
    single<TranslationService> { AndroidTranslationService() }
}