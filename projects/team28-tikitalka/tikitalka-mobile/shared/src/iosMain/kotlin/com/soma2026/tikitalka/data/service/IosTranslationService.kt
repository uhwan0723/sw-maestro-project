package com.soma2026.tikitalka.data.service

import com.soma2026.tikitalka.domain.service.TranslationLanguage
import com.soma2026.tikitalka.domain.service.TranslationService

class IosTranslationService : TranslationService {
    override suspend fun translate(text: String, targetLanguage: TranslationLanguage): Result<String> =
        Result.failure(UnsupportedOperationException("번역이 지원되지 않는 플랫폼입니다"))

    override suspend fun isAvailable(): Boolean = false
}